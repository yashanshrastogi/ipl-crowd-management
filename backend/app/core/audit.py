"""
Structured audit logging helper for security and compliance.
Outputs events as structured JSON objects for ingestion by Cloud Logging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

# Configure a separate logger for security audit events
audit_logger = logging.getLogger("ipl.security.audit")


def log_audit_event(
    action: str,
    actor: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a structured security audit event in JSON format.

    Parameters
    ----------
    action : str
        The operation name (e.g. 'trigger_evacuation', 'update_signage').
    actor : str
        The entity performing the action (e.g. user_id, 'system', API token principal).
    status : str
        The outcome of the operation (e.g. 'SUCCESS', 'FAILED', 'BLOCKED').
    details : dict, optional
        Additional metadata related to the audit context.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "status": status,
        "details": details or {},
    }
    # Log at INFO level with JSON payload
    audit_logger.info(json.dumps(event))
