from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Gesture = Literal[
    "none",
    "raised_hand",
    "pointing",
    "thumbs_up",
    "thumbs_down",
    "open_palm",
    "idle",
]

Attention = Literal["unknown", "focused", "away", "confused", "idle"]
HeadPose = Literal["unknown", "center", "tilted_left", "tilted_right", "looking_down", "looking_away"]
InferenceMode = Literal["mediapipe", "mediapipe_gemma", "gemma_multimodal"]
ReasoningPolicy = Literal["skip", "invoke"]
CognitiveState = Literal["watching", "focused", "confused", "reasoning", "intervening"]


@dataclass(slots=True)
class PerceptionEvent:
    source: str
    gesture: Gesture = "none"
    attention: Attention = "unknown"
    duration: float = 0.0
    head_pose: HeadPose = "unknown"
    input_mode: InferenceMode = "mediapipe_gemma"
    intent_signal: str = "ambient_monitoring"
    raw_gesture: str = "none"
    context: str = "on_device_gemma4_showcase"
    confidence: float = 0.0
    importance: float = 0.0
    reasoning_policy: ReasoningPolicy = "invoke"
    cognitive_state: CognitiveState = "watching"
    landmarks: dict[str, Any] = field(default_factory=dict)
    frame_meta: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpeculativeHint:
    text: str
    intent: str
    confidence: float
    latency_ms: float
    event_id: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReasoningResult:
    intent: str
    should_intervene: bool
    assistance: str
    confidence: float
    actions: list[str]
    raw: str
    model: str
    latency_ms: float
    event_id: str
    token_trace: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentMemory:
    observations: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    max_items: int = 32

    def remember_observation(self, event: PerceptionEvent) -> None:
        self.observations.append(event.to_dict())
        self.observations = self.observations[-self.max_items :]

    def remember_suggestion(self, result: ReasoningResult) -> None:
        self.suggestions.append(result.to_dict())
        self.suggestions = self.suggestions[-self.max_items :]
