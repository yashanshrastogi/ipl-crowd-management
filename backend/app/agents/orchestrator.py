"""
Orchestrator Agent
==================
Master coordinator powered by the Gemini Enterprise Agent Platform.
Monitors live Firestore database states and delegates tasks to
specialised sub-agents when thresholds are broken.

Uses manual tool execution loops — the model proposes tool calls and
sensitive operations are intercepted for human approval before execution.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from google import genai
from google.genai import types

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

# Tools that require human approval before results are acted upon
SENSITIVE_TOOLS = {
    "trigger_evacuation_protocol",
    "update_dynamic_signage",
    "activate_strict_protocol",
}


def _get_genai_client() -> genai.Client:
    """Build a Gemini client from runtime configuration."""
    api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "The orchestrator agent requires a valid Gemini API key."
        )
    return genai.Client(api_key=api_key)


def get_orchestrator_config() -> types.GenerateContentConfig:
    """Build Gemini generation config with automatic tool calls disabled."""
    return types.GenerateContentConfig(
        systemInstruction=SYSTEM_INSTRUCTION,
        tools=TOOL_FUNCTIONS,
        automaticFunctionCalling=types.AutomaticFunctionCallingConfig(disable=True),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Dispatch — Manual Tool Execution Loop (V-07: no auto function calling)
# ═══════════════════════════════════════════════════════════════════════════════

# Map function names to callables for the manual execution loop
_TOOL_MAP: dict[str, Any] = {
    "get_stadium_gate_status": get_stadium_gate_status,
    "update_dynamic_signage": update_dynamic_signage,
    "activate_strict_protocol": activate_strict_protocol,
    "request_pedestrian_reroute": request_pedestrian_reroute,
    "trigger_evacuation_protocol": trigger_evacuation_protocol,
}

# V-06b: Structured input validation constants
PROMPT_MAX_LENGTH = 2000


async def dispatch(prompt: str) -> dict[str, Any]:
    """Send a natural-language directive to the orchestrator agent and
    execute the manual tool-calling loop. Sensitive tools are intercepted
    and require operator confirmation before execution.

    Parameters
    ----------
    prompt : str
        Natural-language instruction.

    Returns
    -------
    dict
        Agent response or pending_approval state if sensitive tool triggered.
    """
    # ── V-06b: Structured input validation (replaces weak keyword blocklist) ──
    if len(prompt) > PROMPT_MAX_LENGTH:
        return {
            "status": "blocked",
            "response": f"Prompt exceeds maximum length of {PROMPT_MAX_LENGTH} characters.",
            "tool_calls": [],
        }

    if not prompt.strip():
        return {
            "status": "blocked",
            "response": "Empty prompt provided.",
            "tool_calls": [],
        }

    # Reject prompts with non-printable characters (homoglyph / injection vectors)
    if not all(c.isprintable() or c.isspace() for c in prompt):
        return {
            "status": "blocked",
            "response": "Prompt contains invalid characters.",
            "tool_calls": [],
        }

    tool_calls_log: list[dict[str, Any]] = []
    client: genai.Client | None = None

    try:
        client = _get_genai_client()
        config = get_orchestrator_config()
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        # Manual tool execution loop — intercept sensitive tools
        max_iterations = 10  # Guard against infinite loops
        for _ in range(max_iterations):
            # Check if the model wants to call functions
            fn_calls = response.function_calls or []

            if not fn_calls:
                # No more function calls — model produced a text response
                break

            # Process each function call
            fn_responses = []
            for fn_call in fn_calls:
                fn_name = fn_call.name
                fn_args = dict(fn_call.args) if fn_call.args else {}

                tool_calls_log.append({
                    "function": fn_name,
                    "args": fn_args,
                })

                # Intercept sensitive tools — require human approval
                if fn_name in SENSITIVE_TOOLS:
                    return {
                        "status": "pending_approval",
                        "action": fn_name,
                        "args": fn_args,
                        "response": (
                            f"The orchestrator agent recommends executing '{fn_name}' "
                            f"with arguments: {fn_args}. Action requires operator confirmation."
                        ),
                        "tool_calls": tool_calls_log,
                    }

                # Execute safe tools
                if fn_name not in _TOOL_MAP:
                    logger.warning("Unknown tool requested: %s", fn_name)
                    result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    try:
                        result = _TOOL_MAP[fn_name](**fn_args)
                    except Exception:
                        logger.exception("Tool %s failed", fn_name)
                        result = {"error": "Tool execution failed"}

                fn_responses.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response=result if isinstance(result, dict) else {"result": str(result)},
                    )
                )

            # Send function results back to the model
            contents.extend(
                [
                    response.candidates[0].content,
                    types.Content(role="tool", parts=fn_responses),
                ]
            )
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )

        return {
            "status": "completed",
            "response": response.text or "",
            "tool_calls": tool_calls_log,
        }
    except Exception:
        logger.exception("Orchestrator dispatch failed")
        return {
            "status": "error",
            "error": "An internal error occurred during agent dispatch. Please try again.",
            "tool_calls": tool_calls_log,
        }
    finally:
        if client is not None:
            client.close()
