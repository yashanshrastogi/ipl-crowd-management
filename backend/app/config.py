"""
Application configuration resolved entirely from environment variables.
Zero hardcoded secrets — all values sourced at runtime via pydantic-settings.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration store.  Every field maps 1-to-1 to an env var."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Google Cloud Platform ──────────────────────────────────────────
    google_cloud_project: str = "ipl-crowd-mgmt-2026"
    google_application_credentials: str = ""

    # ── Gemini AI ──────────────────────────────────────────────────────
    google_api_key: str = ""

    # ── Google Maps ────────────────────────────────────────────────────
    google_maps_api_key: str = ""

    # ── Firestore ──────────────────────────────────────────────────────
    firestore_database: str = "(default)"

    # ── Pub/Sub ────────────────────────────────────────────────────────
    pubsub_topic: str = "crowd-telemetry"
    pubsub_subscription: str = "crowd-telemetry-push"

    # ── BigQuery ───────────────────────────────────────────────────────
    bigquery_dataset: str = "crowd_analytics"
    bigquery_table: str = "telemetry_events"

    # ── Cloud Storage ──────────────────────────────────────────────────
    gcs_bucket: str = "ipl-crowd-mgmt-archive"

    # ── Application ────────────────────────────────────────────────────
    stadium_id: str = "chinnaswamy_stadium"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://ipl-crowd-mgmt-2026.web.app,https://ipl-crowd-mgmt-2026.firebaseapp.com"
    admin_api_key: str = ""  # MUST be set via ADMIN_API_KEY env var


    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Module-level singleton — import this everywhere
settings = Settings()
