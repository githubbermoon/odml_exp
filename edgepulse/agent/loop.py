from __future__ import annotations

from collections import deque

from edgepulse.core.models import AgentMemory, PerceptionEvent, ReasoningResult, SpeculativeHint
from edgepulse.reasoning.litert_lm import LiteRTLMReasoner
from edgepulse.speculative.engine import SpeculativeInteractionEngine


class EdgePulseAgent:
    def __init__(self, window_size: int = 4) -> None:
        self.events: deque[PerceptionEvent] = deque(maxlen=window_size)
        self.memory = AgentMemory()
        self.speculative = SpeculativeInteractionEngine()
        self.reasoner = LiteRTLMReasoner()

    async def observe(self, event: PerceptionEvent) -> tuple[SpeculativeHint, ReasoningResult]:
        self.events.append(event)
        self.memory.remember_observation(event)
        hint = self.speculative.predict(event)
        result = await self.reasoner.reason(list(self.events))
        self.memory.remember_suggestion(result)
        return hint, result

    def instant_hint(self, event: PerceptionEvent) -> SpeculativeHint:
        self.events.append(event)
        self.memory.remember_observation(event)
        return self.speculative.predict(event)

    async def refine(self) -> ReasoningResult:
        result = await self.reasoner.reason(list(self.events))
        self.memory.remember_suggestion(result)
        return result
