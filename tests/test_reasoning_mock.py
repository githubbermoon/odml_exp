import asyncio

from edgepulse.core.models import PerceptionEvent
from edgepulse.reasoning.litert_lm import LiteRTLMReasoner


def test_mock_reasoning_returns_structured_result() -> None:
    async def run():
        reasoner = LiteRTLMReasoner()
        return await reasoner.reason([PerceptionEvent(source="test", gesture="pointing", attention="focused")])

    result = asyncio.run(run())
    assert result.intent == "code_reference"
    assert result.should_intervene is True
    assert result.token_trace


def test_reasoning_parser_extracts_fenced_json_with_logs() -> None:
    reasoner = LiteRTLMReasoner()
    event = PerceptionEvent(source="test")
    parsed = reasoner._parse_or_repair(
        'Warning: cache message\n```json\n{"intent":"ready","should_intervene":false,"assistance":"ok","confidence":0.9,"actions":[]}\n```',
        event,
    )

    assert parsed["intent"] == "ready"
    assert parsed["assistance"] == "ok"
