"""
Orchestrator Agent
==================
Master coordinator powered by the Gemini Enterprise Agent Platform.
Monitors live Firestore database states and delegates tasks to
specialised sub-agents when thresholds are broken.

Uses automatic tool execution loops — the model inspects capacities
and routes crowds autonomously through bound function tools.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import google.generativeai as genai

from app.config import settings
from app.services import firestore_service, maps_service

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Functions — bound to the Gemini model's toolset
# ═══════════════════════════════════════════════════════════════════════════════


def get_stadium_gate_status(stadium_id: str) -> dict[str, Any]:
    """Queries the live state database to retrieve active wait times, crowd
    densities, and security checkpoint throughput metrics for all gates.

    Args:
        stadium_id: Unique venue identifier (e.g., 'chinnaswamy_stadium').
    """
    try:
        gates = firestore_service.get_all_gates(stadium_id)
        return {
            "stadium_id": stadium_id,
            "gate_count": len(gates),
            "gates": gates,
        }
    except Exception as exc:
        logger.exception("Failed to fetch gate status")
        return {"stadium_id": stadium_id, "error": str(exc), "gates": []}


def update_dynamic_signage(gate_id: str, message: str) -> dict[str, Any]:
    """Triggers an API call to physical LED signage control units to display
    live routing directives. Requires manual approval.

    Args:
        gate_id: Identifier of the target gate zone.
        message: The exact directional text instruction to display.
    """
    logger.info("Orchestrator requested update_dynamic_signage (gate=%s, msg=%s) — approval required", gate_id, message)
    return {
        "status": "REQUIRES_OPERATOR_APPROVAL",
        "action": "update_dynamic_signage",
        "gate_id": gate_id,
        "message": message,
        "error": "This action requires manual confirmation from the Safety Chief.",
    }


def activate_strict_protocol(gate_id: str, banned_items: str) -> dict[str, Any]:
    """Activates the Strict Protocol at a gate, broadcasting item restrictions
    to approaching crowds. Requires manual approval.

    Args:
        gate_id: Target gate identifier.
        banned_items: Comma-separated list of banned items (e.g., 'bags,coins,bottles').
    """
    logger.info("Orchestrator requested activate_strict_protocol (gate=%s, items=%s) — approval required", gate_id, banned_items)
    return {
        "status": "REQUIRES_OPERATOR_APPROVAL",
        "action": "activate_strict_protocol",
        "gate_id": gate_id,
        "banned_items": banned_items,
        "error": "This action requires manual confirmation from the Safety Chief.",
    }


def request_pedestrian_reroute(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict[str, Any]:
    """Generates a walking route that circumvents dense bottleneck corridors.

    Args:
        origin_lat: Latitude of the origin point.
        origin_lng: Longitude of the origin point.
        dest_lat: Latitude of the destination point.
        dest_lng: Longitude of the destination point.
    """
    return maps_service.compute_pedestrian_route(origin_lat, origin_lng, dest_lat, dest_lng)


def trigger_evacuation_protocol(
    stadium_id: str, affected_zones: str, reason: str,
) -> dict[str, Any]:
    """Triggers the emergency evacuation protocol across the stadium. Requires manual approval.

    Args:
        stadium_id: Venue identifier.
        affected_zones: Comma-separated list of affected zone IDs.
        reason: Description of the triggering event.
    """
    logger.warning("Orchestrator requested trigger_evacuation_protocol (stadium=%s, zones=%s, reason=%s) — approval required", stadium_id, affected_zones, reason)
    return {
        "status": "REQUIRES_OPERATOR_APPROVAL",
        "action": "trigger_evacuation_protocol",
        "stadium_id": stadium_id,
        "affected_zones": affected_zones,
        "reason": reason,
        "error": "This action requires manual confirmation from the Safety Chief.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Gemini Model Configuration
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_INSTRUCTION = (
    "You are the Master Safety Coordinator Agent for IPL stadium crowd management. "
    "Your responsibilities:\n"
    "1. Use get_stadium_gate_status to inspect live wait times when overcrowding is reported.\n"
    "2. Use update_dynamic_signage to redirect crowd flow to underutilised gates.\n"
    "3. Use activate_strict_protocol when checkpoint latency spikes — broadcast "
    "'Prepare credentials, remove banned items' to approaching crowds.\n"
    "4. Use request_pedestrian_reroute to generate walking paths that avoid congested corridors.\n"
    "5. Use trigger_evacuation_protocol ONLY for confirmed life-safety emergencies.\n\n"
    "CRITICAL RULES:\n"
    "- Always verify gate status BEFORE making routing changes.\n"
    "- Never trigger evacuation without confirming sensor data indicates genuine hazard.\n"
    "- Provide clear, actionable instructions in all signage messages.\n"
    "- Prioritise crowd safety above all operational concerns."
)

TOOL_FUNCTIONS = [
    get_stadium_gate_status,
    update_dynamic_signage,
    activate_strict_protocol,
    request_pedestrian_reroute,
    trigger_evacuation_protocol,
]


def _configure_genai() -> None:
    """Ensure the Gemini SDK is configured with the API key."""
    api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "The orchestrator agent requires a valid Gemini API key."
        )
    genai.configure(api_key=api_key)


def get_orchestrator_model() -> genai.GenerativeModel:
    """Build and return a configured Gemini model with bound tools."""
    _configure_genai()
    return genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=TOOL_FUNCTIONS,
        system_instruction=SYSTEM_INSTRUCTION,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Dispatch — Automatic Tool Execution Loop
# ═══════════════════════════════════════════════════════════════════════════════

# Map function names to callables for the automatic execution loop
_TOOL_MAP: dict[str, Any] = {
    "get_stadium_gate_status": get_stadium_gate_status,
    "update_dynamic_signage": update_dynamic_signage,
    "activate_strict_protocol": activate_strict_protocol,
    "request_pedestrian_reroute": request_pedestrian_reroute,
    "trigger_evacuation_protocol": trigger_evacuation_protocol,
}


async def dispatch(prompt: str) -> dict[str, Any]:
    """Send a natural-language directive to the orchestrator agent and
    execute the full tool-calling loop until the model produces a final
    text response. Contains prompt validation and tool interception.

    Parameters
    ----------
    prompt : str
        Natural-language instruction.

    Returns
    -------
    dict
        Agent response or pending_approval state if sensitive tool triggered.
    """
    # ── Prompt Injection Guard ──
    injection_keywords = ["ignore", "override", "bypass", "system instruction", "you are no longer", "ignore previous"]
    prompt_lower = prompt.lower()
    if any(keyword in prompt_lower for keyword in injection_keywords):
        return {
            "status": "blocked",
            "response": "Input directive blocked due to security validation failure (potential instruction override).",
            "tool_calls": [],
        }

    model = get_orchestrator_model()
    chat = model.start_chat(enable_automatic_function_calling=True)

    tool_calls_log: list[dict[str, Any]] = []

    import asyncio
    try:
        response = await asyncio.to_thread(chat.send_message, prompt)

        # Log all tool calls that were auto-executed
        for content in chat.history:
            for part in content.parts:
                if fn_call := part.function_call:
                    tool_calls_log.append({
                        "function": fn_call.name,
                        "args": dict(fn_call.args),
                    })

        # Intercept and check if any sensitive tool calls were generated
        for call in tool_calls_log:
            fn_name = call["function"]
            if fn_name in ["trigger_evacuation_protocol", "update_dynamic_signage", "activate_strict_protocol"]:
                return {
                    "status": "pending_approval",
                    "action": fn_name,
                    "args": call["args"],
                    "response": (
                        f"The orchestrator agent recommends executing '{fn_name}' "
                        f"with arguments: {call['args']}. Action requires operator confirmation."
                    ),
                    "tool_calls": tool_calls_log,
                }

        return {
            "status": "completed",
            "response": response.text if response.text else "",
            "tool_calls": tool_calls_log,
        }
    except Exception as exc:
        logger.exception("Orchestrator dispatch failed")
        return {
            "status": "error",
            "error": str(exc),
            "tool_calls": tool_calls_log,
        }
