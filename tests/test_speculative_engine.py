from edgepulse.core.models import PerceptionEvent
from edgepulse.speculative.engine import SpeculativeInteractionEngine


def test_raised_hand_gets_fast_help_hint() -> None:
    event = PerceptionEvent(source="test", gesture="raised_hand", attention="focused", confidence=0.9)
    hint = SpeculativeInteractionEngine().predict(event)

    assert hint.intent == "audience_question"
    assert "gemma 4" in hint.text.lower()
    assert hint.latency_ms < 100
