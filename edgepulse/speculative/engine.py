from __future__ import annotations

import time

from edgepulse.core.models import PerceptionEvent, SpeculativeHint


class SpeculativeInteractionEngine:
    """Fast heuristic layer that makes the UI react before LLM reasoning finishes.

    This intentionally does not implement speculative decoding internals. It mirrors
    the product feel of MTP/drafter systems by showing cheap predictions within a
    frame budget, then letting the local model refine the answer.
    """

    def predict(self, event: PerceptionEvent) -> SpeculativeHint:
        started = time.perf_counter()
        text, intent, confidence = self._route(event)
        return SpeculativeHint(
            text=text,
            intent=intent,
            confidence=confidence,
            latency_ms=(time.perf_counter() - started) * 1000,
            event_id=event.event_id,
        )

    def _route(self, event: PerceptionEvent) -> tuple[str, str, float]:
        if event.gesture == "raised_hand":
            return "Audience question detected. Preparing a Gemma 4 answer...", "audience_question", 0.86
        if event.gesture == "pointing":
            return "Pipeline reference detected. Inspecting the ODML path...", "pipeline_reference", 0.78
        if event.gesture == "thumbs_up":
            return "Acknowledged. I will keep monitoring quietly.", "approval", 0.9
        if event.gesture == "thumbs_down":
            return "That did not look right. Preparing a concise alternative...", "negative_feedback", 0.83
        if event.attention == "confused" or event.head_pose in {"tilted_left", "tilted_right"}:
            return "Stack question detected. Separating MediaPipe, LiteRT-LM, and Gemma 4...", "stack_explanation", 0.72
        if event.attention == "idle" or event.gesture == "idle":
            return "Idle moment detected. I can summarize the current thread...", "idle_summary", 0.65
        if event.attention == "focused" and event.duration >= 5:
            return "Sustained focus detected. I will stay ambient unless interrupted.", "ambient_monitoring", 0.58
        return "Monitoring locally...", "ambient_monitoring", 0.45
