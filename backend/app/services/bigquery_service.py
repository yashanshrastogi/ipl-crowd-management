"""
BigQuery Service
================
Streaming inserts and query methods for the long-term analytical warehouse.
Uses the append-only pattern specified in the architecture — raw telemetry
events are never mutated after write.

Table: {dataset}.telemetry_events
"""

from __future__ import annotations

import logging
from typing import Any

from google.api_core import exceptions as google_exceptions  # type: ignore[import-untyped]
from google.auth import exceptions as auth_exceptions  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

from app.config import settings

logger = logging.getLogger(__name__)

_client: bigquery.Client | None = None
_client_unavailable = False


def _is_local_fallback_allowed() -> bool:
    return settings.app_env != "production"


def _get_client() -> bigquery.Client | None:
    """Lazy-initialise a BigQuery client singleton."""
    global _client, _client_unavailable  # noqa: PLW0603
    if _client_unavailable:
        return None
    if _client is None:
        try:
            _client = bigquery.Client(project=settings.google_cloud_project)
            logger.info("BigQuery client initialised")
        except auth_exceptions.GoogleAuthError:
            if not _is_local_fallback_allowed():
                raise
            _client_unavailable = True
            logger.warning("BigQuery credentials unavailable; analytics writes disabled locally")
            return None
    return _client


def _is_recoverable_service_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            auth_exceptions.GoogleAuthError,
            google_exceptions.GoogleAPICallError,
            google_exceptions.RetryError,
        ),
    )


def _disable_after_error(exc: Exception) -> bool:
    global _client_unavailable  # noqa: PLW0603
    if not _is_local_fallback_allowed() or not _is_recoverable_service_error(exc):
        return False
    _client_unavailable = True
    logger.warning("BigQuery unavailable; analytics operations disabled locally: %s", exc)
    return True


def _table_ref() -> str:
    """Fully-qualified table reference."""
    return f"{settings.google_cloud_project}.{settings.bigquery_dataset}.{settings.bigquery_table}"


# ── Schema Bootstrap ──────────────────────────────────────────────────────────

TELEMETRY_SCHEMA = [
    bigquery.SchemaField("stadium_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("gate_id", "STRING"),
    bigquery.SchemaField("zone_id", "STRING"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("density", "FLOAT"),
    bigquery.SchemaField("velocity", "FLOAT"),
    bigquery.SchemaField("estimated_count", "INTEGER"),
    bigquery.SchemaField(
        "sensor_readings",
        "RECORD",
        mode="REPEATED",
        fields=[
            bigquery.SchemaField("sensor_type", "STRING"),
            bigquery.SchemaField("value", "FLOAT"),
            bigquery.SchemaField("unit", "STRING"),
        ],
    ),
]


def ensure_dataset_and_table() -> None:
    """Create the BigQuery dataset and table if they don't exist yet."""
    client = _get_client()
    if client is None:
        return

    dataset_ref = bigquery.DatasetReference(settings.google_cloud_project, settings.bigquery_dataset)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    try:
        client.create_dataset(dataset, exists_ok=True)
        logger.info("Dataset %s ensured", settings.bigquery_dataset)

        table_ref = dataset_ref.table(settings.bigquery_table)
        table = bigquery.Table(table_ref, schema=TELEMETRY_SCHEMA)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp",
        )
        client.create_table(table, exists_ok=True)
        logger.info("Table %s ensured", settings.bigquery_table)
    except Exception as exc:
        if not _disable_after_error(exc):
            raise


# ── Streaming Insert ─────────────────────────────────────────────────────────


def insert_telemetry_row(row: dict[str, Any]) -> None:
    """Append a single telemetry row via the streaming insert API."""
    client = _get_client()
    if client is None:
        logger.debug("BigQuery insert skipped because analytics is disabled locally")
        return
    try:
        errors = client.insert_rows_json(_table_ref(), [row])
    except Exception as exc:
        if not _disable_after_error(exc):
            raise
        return
    if errors:
        logger.error("BigQuery streaming insert errors: %s", errors)


def insert_telemetry_rows(rows: list[dict[str, Any]]) -> None:
    """Batch insert multiple telemetry rows."""
    if not rows:
        return
    client = _get_client()
    if client is None:
        logger.debug("BigQuery batch insert skipped because analytics is disabled locally")
        return
    try:
        errors = client.insert_rows_json(_table_ref(), rows)
    except Exception as exc:
        if not _disable_after_error(exc):
            raise
        return
    if errors:
        logger.error("BigQuery batch insert errors: %s", errors)


# ── Queries ───────────────────────────────────────────────────────────────────


def query_gate_history(
    stadium_id: str,
    gate_id: str,
    hours: int = 24,
) -> list[dict[str, Any]]:
    """Retrieve recent telemetry for a specific gate."""
    client = _get_client()
    if client is None:
        return []
    sql = f"""
        SELECT *
        FROM `{_table_ref()}`
        WHERE stadium_id = @stadium_id
          AND gate_id = @gate_id
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
        ORDER BY timestamp DESC
        LIMIT 500
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stadium_id", "STRING", stadium_id),
            bigquery.ScalarQueryParameter("gate_id", "STRING", gate_id),
            bigquery.ScalarQueryParameter("hours", "INT64", hours),
        ]
    )
    try:
        results = client.query(sql, job_config=job_config).result()
    except Exception as exc:
        if not _disable_after_error(exc):
            raise
        return []
    return [dict(row) for row in results]


def query_density_summary(stadium_id: str, hours: int = 1) -> list[dict[str, Any]]:
    """Aggregate average density per gate over a time window."""
    client = _get_client()
    if client is None:
        return []
    sql = f"""
        SELECT
            gate_id,
            AVG(density) AS avg_density,
            MAX(density) AS max_density,
            COUNT(*) AS reading_count
        FROM `{_table_ref()}`
        WHERE stadium_id = @stadium_id
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
        GROUP BY gate_id
        ORDER BY avg_density DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stadium_id", "STRING", stadium_id),
            bigquery.ScalarQueryParameter("hours", "INT64", hours),
        ]
    )
    try:
        results = client.query(sql, job_config=job_config).result()
    except Exception as exc:
        if not _disable_after_error(exc):
            raise
        return []
    return [dict(row) for row in results]
