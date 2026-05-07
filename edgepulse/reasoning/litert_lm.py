from __future__ import annotations

import asyncio
import json
import os
import shlex
import time
from collections.abc import AsyncIterator

from edgepulse.core.models import PerceptionEvent, ReasoningResult


PROMPT_TEMPLATE = """You are an on-device multimodal reasoning agent.

Input events:
{events_json}

Infer:
1. probable user intent
2. whether intervention is useful
3. best concise assistance
4. confidence score

Respect sparse semantic reasoning: intervene only when the compressed event is important enough.
Never request or assume continuous raw video. Treat landmarks and frame metadata as compressed perception only.

Respond in compact structured JSON with keys:
intent, should_intervene, assistance, confidence, actions.
"""

VISION_PROMPT_TEMPLATE = """You are SecondSight, a local camera-to-text scene narrator.

There is exactly one camera image attached before this text. Inspect that attached image.
Do not ask the user to provide an image unless the runtime reports that the attachment is unreadable.

Input event:
{event_json}

Use the attached image and event JSON to answer:
1. what visible context matters
2. probable user intent
3. whether intervention is useful
4. best concise assistance
5. confidence score

Prefer plain scene details and visible evidence over broad assistant behavior.

Respond in compact structured JSON with keys:
intent, should_intervene, assistance, confidence, actions.
"""

CAPTURE_EXTRACTION_PROMPT = """You are SecondSight, a local camera-to-text scene extractor.

Inspect the attached image and return compact JSON with keys:
caption: one short sentence describing the scene
objects: array of visible objects or surfaces
visible_text: any readable text, or empty string
summary: useful details worth remembering for later questions
tags: 3 to 8 short lowercase tags

Do not invent details that are not visible.
"""

CAPTURE_QUESTION_PROMPT = """You answer questions from locally saved SecondSight captures.

Question:
{question}

Relevant saved captures:
{captures_json}

Answer in one concise paragraph. If the captures do not contain enough evidence, say what is missing.
"""


class LiteRTLMReasoner:
    """Local Gemma/LiteRT-LM adapter.

    Configure EDGEPULSE_LITERT_CMD with a command that accepts the prompt on stdin
    and streams tokens/stdout. Without it, EdgePulse uses a deterministic offline
    path for demo development.
    """

    def __init__(self, model_name: str = "gemma-e2b-litert-lm") -> None:
        self.model_name = os.getenv("EDGEPULSE_MODEL", model_name)
        self.command = os.getenv("EDGEPULSE_LITERT_CMD", "").strip()
        self.vision_command = os.getenv("EDGEPULSE_LITERT_VISION_CMD", "").strip()

    async def reason_stream(self, events: list[PerceptionEvent], frame: dict[str, object] | None = None) -> AsyncIterator[str]:
        if frame:
            prompt = VISION_PROMPT_TEMPLATE.format(events_json="", event_json=json.dumps(events[-1].to_dict(), indent=2))
            if self.vision_command:
                async for token in self._run_litert_vision_command(prompt, frame):
                    yield token
                return
            yield json.dumps(
                {
                    "intent": "multimodal_runner_unconfigured",
                    "should_intervene": True,
                    "assistance": "Direct Gemma vision mode captured a frame, but EDGEPULSE_LITERT_VISION_CMD is not configured yet. Use MediaPipe + Gemma for the live path or add an image-capable LiteRT-LM wrapper.",
                    "confidence": 0.3,
                    "actions": ["configure_litert_vision_runner", "fall_back_to_mediapipe_gemma"],
                }
            )
            return

        prompt = PROMPT_TEMPLATE.format(events_json=json.dumps([e.to_dict() for e in events], indent=2))
        if self.command:
            async for token in self._run_litert_command(prompt):
                yield token
            return

        for token in self._mock_reasoning(events):
            await asyncio.sleep(0.025)
            yield token

    async def reason(self, events: list[PerceptionEvent]) -> ReasoningResult:
        started = time.perf_counter()
        tokens: list[str] = []
        async for token in self.reason_stream(events):
            tokens.append(token)
        raw = "".join(tokens)
        parsed = self._parse_or_repair(raw, events[-1])
        return ReasoningResult(
            intent=str(parsed["intent"]),
            should_intervene=bool(parsed["should_intervene"]),
            assistance=str(parsed["assistance"]),
            confidence=float(parsed["confidence"]),
            actions=list(parsed.get("actions", [])),
            raw=raw,
            model=self.model_name,
            latency_ms=(time.perf_counter() - started) * 1000,
            event_id=events[-1].event_id,
            token_trace=tokens,
        )

    async def extract_capture_details(self, frame: dict[str, object]) -> dict[str, object]:
        if self.vision_command:
            tokens: list[str] = []
            async for token in self._run_litert_vision_command(CAPTURE_EXTRACTION_PROMPT, frame):
                tokens.append(token)
            raw = "".join(tokens)
            parsed = self._parse_capture_json(raw)
            parsed["raw"] = raw
            parsed["status"] = "ready"
            return parsed
        return {
            "caption": "Image saved locally. Vision extraction is not configured in this runtime.",
            "objects": [],
            "visible_text": "",
            "summary": "A camera frame was saved, but EDGEPULSE_LITERT_VISION_CMD is not configured.",
            "tags": ["saved", "unprocessed"],
            "status": "unprocessed",
            "raw": "",
        }

    async def answer_capture_question(self, question: str, captures: list[dict[str, object]]) -> str:
        if not captures:
            return "I do not have any saved image details to answer from yet."
        if self.command:
            prompt = CAPTURE_QUESTION_PROMPT.format(question=question, captures_json=json.dumps(captures, indent=2))
            tokens: list[str] = []
            async for token in self._run_litert_command(prompt):
                tokens.append(token)
            return "".join(tokens).strip()
        return self._fallback_capture_answer(question, captures)

    async def _run_litert_command(self, prompt: str) -> AsyncIterator[str]:
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(self.command),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        while True:
            chunk = await proc.stdout.read(24)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")

        code = await proc.wait()
        if code != 0:
            stderr = await proc.stderr.read() if proc.stderr else b""
            yield json.dumps(
                {
                    "intent": "runtime_error",
                    "should_intervene": True,
                    "assistance": f"LiteRT-LM runner failed: {stderr.decode('utf-8', errors='replace')[:180]}",
                    "confidence": 0.2,
                    "actions": ["check_litert_lm_command"],
                }
            )

    async def _run_litert_vision_command(self, prompt: str, frame: dict[str, object]) -> AsyncIterator[str]:
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(self.vision_command),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout
        proc.stdin.write(json.dumps({"prompt": prompt, "frame": frame}).encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        while True:
            chunk = await proc.stdout.read(24)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")

        code = await proc.wait()
        if code != 0:
            stderr = await proc.stderr.read() if proc.stderr else b""
            yield json.dumps(
                {
                    "intent": "runtime_error",
                    "should_intervene": True,
                    "assistance": f"LiteRT-LM vision runner failed: {stderr.decode('utf-8', errors='replace')[:180]}",
                    "confidence": 0.2,
                    "actions": ["check_litert_vision_command"],
                }
            )

    def _mock_reasoning(self, events: list[PerceptionEvent]) -> list[str]:
        event = events[-1]
        if event.intent_signal == "focus_assistant" or event.gesture == "raised_hand":
            payload = {
                "intent": "focus_assistant",
                "should_intervene": True,
                "assistance": "You paused at the focus point. I can compress the current thread into one next step.",
                "confidence": 0.86,
                "actions": ["offer_summary", "preserve_focus_context"],
            }
        elif event.intent_signal == "meeting_cognition" or event.gesture == "pointing":
            payload = {
                "intent": "meeting_cognition",
                "should_intervene": True,
                "assistance": "Whiteboard-style context detected. I am storing the topic, open questions, and likely follow-up actions.",
                "confidence": 0.78,
                "actions": ["summarize_topic", "extract_todos"],
            }
        elif event.intent_signal == "confusion_trace" or event.attention == "confused":
            payload = {
                "intent": "confusion_support",
                "should_intervene": True,
                "assistance": "Confusion spike captured. Break the edge-AI stack into perception, compression, sparse reasoning, and memory.",
                "confidence": 0.74,
                "actions": ["mark_confusion", "offer_clarification"],
            }
        else:
            payload = {
                "intent": "ambient_monitoring",
                "should_intervene": False,
                "assistance": "Keep monitoring quietly and preserve local context for a future assist.",
                "confidence": 0.55,
                "actions": ["remember_context"],
            }
        text = json.dumps(payload)
        return [text[i : i + 10] for i in range(0, len(text), 10)]

    def _parse_or_repair(self, raw: str, event: PerceptionEvent) -> dict[str, object]:
        raw_json = self._extract_json(raw)
        try:
            parsed = json.loads(raw_json)
            return {
                "intent": parsed.get("intent", "unknown"),
                "should_intervene": parsed.get("should_intervene", False),
                "assistance": parsed.get("assistance", raw[:240]),
                "confidence": parsed.get("confidence", 0.4),
                "actions": parsed.get("actions", []),
            }
        except json.JSONDecodeError:
            return {
                "intent": "unstructured_reasoning",
                "should_intervene": event.gesture != "none",
                "assistance": raw[:360],
                "confidence": 0.45,
                "actions": ["review_stream"],
            }

    def _extract_json(self, raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    def _parse_capture_json(self, raw: str) -> dict[str, object]:
        try:
            parsed = json.loads(self._extract_json(raw))
            return {
                "caption": str(parsed.get("caption", "")),
                "objects": list(parsed.get("objects", [])) if isinstance(parsed.get("objects", []), list) else [],
                "visible_text": str(parsed.get("visible_text", "")),
                "summary": str(parsed.get("summary", parsed.get("caption", ""))),
                "tags": list(parsed.get("tags", [])) if isinstance(parsed.get("tags", []), list) else [],
            }
        except json.JSONDecodeError:
            return {
                "caption": raw[:180],
                "objects": [],
                "visible_text": "",
                "summary": raw[:360],
                "tags": ["unstructured"],
            }

    def _fallback_capture_answer(self, question: str, captures: list[dict[str, object]]) -> str:
        excerpts = []
        for capture in captures[:3]:
            summary = str(capture.get("summary") or capture.get("caption") or "").strip()
            visible_text = str(capture.get("visible_text") or "").strip()
            objects = ", ".join(str(item) for item in capture.get("objects", []) or [])
            parts = [part for part in [summary, f"Visible text: {visible_text}" if visible_text else "", f"Objects: {objects}" if objects else ""] if part]
            if parts:
                excerpts.append(" ".join(parts))
        if excerpts:
            return "From the saved captures: " + " ".join(excerpts)
        return f"I found saved captures, but they do not include extracted details that answer: {question}"
