"""
Apache Beam Pipeline for Cloud Dataflow
========================================
Implements stateful sliding-window aggregations to calculate live gate
wait times with exactly-once processing guarantees.

Windowing: 30-second sliding windows with 10-second slide period.

Deploy to Dataflow:
    python beam_pipeline.py \
        --runner DataflowRunner \
        --project ipl-crowd-mgmt-2026 \
        --region us-central1 \
        --temp_location gs://ipl-crowd-mgmt-archive/temp \
        --staging_location gs://ipl-crowd-mgmt-archive/staging
"""

from __future__ import annotations

import argparse
import json
import logging

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import SlidingWindows

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
WINDOW_SIZE_SEC = 30
WINDOW_SLIDE_SEC = 10
V_MAX = 1.34
A_FOOTPRINT = 0.26


# ── Transforms ────────────────────────────────────────────────────────────────


class ParseTelemetry(beam.DoFn):
    """Parse JSON telemetry payloads from Pub/Sub messages."""

    def process(self, element):
        try:
            data = json.loads(element.decode("utf-8"))
            gate_id = data.get("gate_id", "unknown")
            density = float(data.get("crowd_density", 0))
            timestamp = data.get("timestamp", "")
            yield (gate_id, {
                "density": density,
                "timestamp": timestamp,
                "zone_id": data.get("zone_id", ""),
                "estimated_count": data.get("estimated_count", 0),
            })
        except Exception as exc:
            logger.error("Failed to parse telemetry: %s", exc)


class ComputeGateAggregates(beam.DoFn):
    """Compute sliding-window aggregates per gate."""

    def process(self, element, window=beam.DoFn.WindowParam):
        gate_id, readings = element
        readings_list = list(readings)

        if not readings_list:
            return

        densities = [r["density"] for r in readings_list]
        avg_density = sum(densities) / len(densities)
        max_density = max(densities)

        # Compute velocity using the non-linear model
        velocity = max(V_MAX * (1.0 - A_FOOTPRINT * avg_density), 0.0)
        flow_rate = avg_density * velocity * 3.0  # Default 3m effective width

        # Risk classification
        if avg_density >= 4.0:
            risk = "CRITICAL"
        elif avg_density >= 1.5:
            risk = "WARNING"
        elif avg_density >= 1.0:
            risk = "ELEVATED"
        else:
            risk = "NORMAL"

        yield {
            "gate_id": gate_id,
            "window_start": window.start.to_utc_datetime().isoformat(),
            "window_end": window.end.to_utc_datetime().isoformat(),
            "reading_count": len(readings_list),
            "avg_density": round(avg_density, 4),
            "max_density": round(max_density, 4),
            "velocity": round(velocity, 4),
            "flow_rate": round(flow_rate, 4),
            "risk_level": risk,
        }


class FormatForBigQuery(beam.DoFn):
    """Format aggregate records for BigQuery insertion."""

    def process(self, element):
        yield {
            "gate_id": element["gate_id"],
            "window_start": element["window_start"],
            "window_end": element["window_end"],
            "reading_count": element["reading_count"],
            "avg_density": element["avg_density"],
            "max_density": element["max_density"],
            "velocity": element["velocity"],
            "flow_rate": element["flow_rate"],
            "risk_level": element["risk_level"],
        }


# ── Pipeline ──────────────────────────────────────────────────────────────────


def run(argv=None):
    """Build and execute the Beam pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_subscription",
        default="projects/ipl-crowd-mgmt-2026/subscriptions/crowd-telemetry-dataflow",
        help="Pub/Sub subscription to read from",
    )
    parser.add_argument(
        "--output_table",
        default="ipl-crowd-mgmt-2026:crowd_analytics.gate_aggregates",
        help="BigQuery output table (project:dataset.table)",
    )

    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(
        pipeline_args,
        streaming=True,
    )

    with beam.Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(
                subscription=known_args.input_subscription,
            )
            | "ParseTelemetry" >> beam.ParDo(ParseTelemetry())
            | "SlidingWindows" >> beam.WindowInto(
                SlidingWindows(size=WINDOW_SIZE_SEC, period=WINDOW_SLIDE_SEC)
            )
            | "GroupByGate" >> beam.GroupByKey()
            | "ComputeAggregates" >> beam.ParDo(ComputeGateAggregates())
            | "FormatForBQ" >> beam.ParDo(FormatForBigQuery())
            | "WriteToBigQuery" >> beam.io.WriteToBigQuery(
                known_args.output_table,
                schema=(
                    "gate_id:STRING,"
                    "window_start:TIMESTAMP,"
                    "window_end:TIMESTAMP,"
                    "reading_count:INTEGER,"
                    "avg_density:FLOAT,"
                    "max_density:FLOAT,"
                    "velocity:FLOAT,"
                    "flow_rate:FLOAT,"
                    "risk_level:STRING"
                ),
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
