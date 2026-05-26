from __future__ import annotations

import pytest
from google.genai import types

from app.agents import orchestrator


@pytest.mark.asyncio
async def test_dispatch_blocks_empty_prompt():
    result = await orchestrator.dispatch("   ")

    assert result["status"] == "blocked"
    assert result["tool_calls"] == []


@pytest.mark.asyncio
async def test_dispatch_blocks_overlong_prompt():
    result = await orchestrator.dispatch("x" * (orchestrator.PROMPT_MAX_LENGTH + 1))

    assert result["status"] == "blocked"
    assert "maximum length" in result["response"]


@pytest.mark.asyncio
async def test_dispatch_intercepts_sensitive_tool_before_execution(monkeypatch):
    class FakeModels:
        def generate_content(self, **_kwargs):
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    function_call=types.FunctionCall(
                                        name="trigger_evacuation_protocol",
                                        args={
                                            "stadium_id": "test_stadium",
                                            "affected_zones": "zone_a",
                                            "reason": "model recommendation",
                                        },
                                    )
                                )
                            ]
                        )
                    )
                ]
            )

    class FakeClient:
        models = FakeModels()

        def close(self):
            pass

    def forbidden_tool(**_kwargs):
        raise AssertionError("Sensitive tool must not execute without approval")

    monkeypatch.setattr(orchestrator, "_get_genai_client", lambda: FakeClient())
    monkeypatch.setitem(
        orchestrator._TOOL_MAP,
        "trigger_evacuation_protocol",
        forbidden_tool,
    )

    result = await orchestrator.dispatch("trigger evacuation")

    assert result["status"] == "pending_approval"
    assert result["action"] == "trigger_evacuation_protocol"
    assert result["tool_calls"][0]["function"] == "trigger_evacuation_protocol"
