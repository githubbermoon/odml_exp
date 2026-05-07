from __future__ import annotations

import socket
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from edgepulse.agent.loop import EdgePulseAgent
from edgepulse.core.models import PerceptionEvent, ReasoningResult


WEB_DIR = Path(__file__).resolve().parents[1] / "web"
INFERENCE_MODES = {
    "mediapipe": "ODML / MediaPipe fast path",
    "mediapipe_gemma": "ODML / MediaPipe + Gemma 4 text",
    "gemma_multimodal": "Direct Gemma 4 vision",
}


def create_app() -> FastAPI:
    app = FastAPI(title="EdgePulse Edge Runtime", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    agent = EdgePulseAgent()
    state: dict[str, Any] = {
        "events": [],
        "hints": [],
        "reasoning": [],
        "latency": [],
        "tokens": [],
        "started_at": time.time(),
        "tailscale_ip": tailscale_ip(),
        "host": socket.gethostname(),
        "mode": "browser-pwa-mvp",
        "inference_mode": "mediapipe_gemma",
        "available_inference_modes": INFERENCE_MODES,
        "model_status": "mock fallback" if not agent.reasoner.command else "text runner configured",
    }
    subscribers: set[WebSocket] = set()
    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def pwa_home() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/manifest.json")
    async def manifest() -> FileResponse:
        return FileResponse(WEB_DIR / "manifest.json")

    @app.get("/sw.js")
    async def service_worker() -> FileResponse:
        return FileResponse(WEB_DIR / "sw.js")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "host": socket.gethostname(), "tailscale_ip": state["tailscale_ip"]}

    @app.get("/network-info")
    async def network_info() -> dict[str, Any]:
        current_tailscale_ip = tailscale_ip()
        current_tailscale_dns = tailscale_dns_name()
        state["tailscale_ip"] = current_tailscale_ip
        return {
            "host": state["host"],
            "tailscale_ip": current_tailscale_ip,
            "tailscale_dns": current_tailscale_dns,
            "http_url": "http://127.0.0.1:8501",
            "tailscale_http_url": f"http://{current_tailscale_ip}:8501" if current_tailscale_ip else None,
            "tailscale_https_url": f"https://{current_tailscale_dns}/" if current_tailscale_dns else None,
            "tailscale_https_hint": "Use `tailscale serve --bg http://127.0.0.1:8501` for camera-safe HTTPS.",
            "inference_mode": state["inference_mode"],
            "available_inference_modes": INFERENCE_MODES,
            "model_status": state["model_status"],
        }

    @app.get("/state")
    async def latest_state() -> dict[str, Any]:
        return state

    @app.post("/events")
    async def post_event(payload: dict[str, Any]) -> dict[str, Any]:
        await handle_event(payload)
        return {"ok": True}

    @app.websocket("/ws/events")
    async def event_socket(ws: WebSocket) -> None:
        await ws.accept()
        subscribers.add(ws)
        await ws.send_json({"type": "snapshot", "state": state})
        try:
            while True:
                payload = await ws.receive_json()
                if payload.get("type") == "set_mode":
                    await set_inference_mode(str(payload.get("mode", "")))
                    continue
                await handle_event(payload)
        except (WebSocketDisconnect, RuntimeError):
            subscribers.discard(ws)
            return

    @app.websocket("/ws/stream")
    async def stream_socket(ws: WebSocket) -> None:
        await ws.accept()
        subscribers.add(ws)
        await ws.send_json({"type": "snapshot", "state": state})
        try:
            while True:
                await ws.receive_text()
        except (WebSocketDisconnect, RuntimeError):
            subscribers.discard(ws)

    async def handle_event(payload: dict[str, Any]) -> None:
        input_mode = normalize_inference_mode(str(payload.get("input_mode") or state["inference_mode"]))
        frame = payload.get("frame") if isinstance(payload.get("frame"), dict) else None
        frame_meta = frame_metadata(frame)
        event_kwargs = {
            "source": str(payload.get("source", "unknown")),
            "gesture": payload.get("gesture", "none"),
            "attention": payload.get("attention", "unknown"),
            "duration": float(payload.get("duration", 0.0)),
            "head_pose": payload.get("head_pose", "unknown"),
            "input_mode": input_mode,
            "intent_signal": str(payload.get("intent_signal", "ambient_monitoring")),
            "raw_gesture": str(payload.get("raw_gesture", payload.get("gesture", "none"))),
            "context": str(payload.get("context", "on_device_gemma4_showcase")),
            "confidence": float(payload.get("confidence", 0.0)),
            "landmarks": dict(payload.get("landmarks", {})),
            "frame_meta": frame_meta,
            "ts": float(payload.get("ts", time.time())),
        }
        event_id = str(payload.get("event_id", payload.get("id", "")))
        if event_id:
            event_kwargs["event_id"] = event_id
        event = PerceptionEvent(**event_kwargs)

        hint = agent.instant_hint(event)
        append_bounded(state["events"], event.to_dict())
        append_bounded(state["hints"], hint.to_dict())
        await broadcast(subscribers, {"type": "hint", "hint": hint.to_dict(), "event": event.to_dict()})

        if input_mode == "mediapipe":
            result = ReasoningResult(
                intent=hint.intent,
                should_intervene=hint.intent not in {"ambient_monitoring"},
                assistance=f"MediaPipe-only mode: {hint.text}",
                confidence=hint.confidence,
                actions=["heuristic_speculative_hint"],
                raw="",
                model="mediapipe-heuristics",
                latency_ms=hint.latency_ms,
                event_id=event.event_id,
                token_trace=[],
            )
            agent.memory.remember_suggestion(result)
            append_bounded(state["reasoning"], result.to_dict())
            await broadcast(subscribers, {"type": "reasoning", "result": result.to_dict()})
            return

        started = time.perf_counter()
        tokens: list[str] = []
        reasoning_frame = frame or {"missing": True} if input_mode == "gemma_multimodal" else None
        state["model_status"] = "streaming"
        await broadcast(subscribers, {"type": "model_status", "mode": input_mode, "status": state["model_status"]})
        async for token in agent.reasoner.reason_stream(list(agent.events), frame=reasoning_frame):
            tokens.append(token)
            token_payload = {
                "event_id": event.event_id,
                "token": token,
                "index": len(tokens) - 1,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "ts": time.time(),
            }
            append_bounded(state["tokens"], token_payload, limit=128)
            await broadcast(subscribers, {"type": "token", **token_payload})

        raw = "".join(tokens)
        parsed = agent.reasoner._parse_or_repair(raw, event)
        result = ReasoningResult(
            intent=str(parsed["intent"]),
            should_intervene=bool(parsed["should_intervene"]),
            assistance=str(parsed["assistance"]),
            confidence=float(parsed["confidence"]),
            actions=list(parsed.get("actions", [])),
            raw=raw,
            model=agent.reasoner.model_name,
            latency_ms=(time.perf_counter() - started) * 1000,
            event_id=event.event_id,
            token_trace=tokens,
        )
        agent.memory.remember_suggestion(result)
        append_bounded(state["reasoning"], result.to_dict())
        append_bounded(
            state["latency"],
            {
                "event_id": event.event_id,
                "speculative_ms": hint.latency_ms,
                "reasoning_ms": result.latency_ms,
                "total_ms": hint.latency_ms + result.latency_ms,
                "ts": time.time(),
            },
        )
        state["model_status"] = "ready"
        await broadcast(subscribers, {"type": "model_status", "mode": input_mode, "status": state["model_status"]})
        await broadcast(subscribers, {"type": "reasoning", "result": result.to_dict()})

    async def set_inference_mode(mode: str) -> None:
        normalized = normalize_inference_mode(mode)
        state["inference_mode"] = normalized
        if normalized == "mediapipe":
            state["model_status"] = "bypassed"
        elif normalized == "gemma_multimodal":
            state["model_status"] = "vision runner configured" if agent.reasoner.vision_command else "vision runner missing"
        else:
            state["model_status"] = "text runner configured" if agent.reasoner.command else "mock fallback"
        await broadcast(
            subscribers,
            {
                "type": "mode",
                "mode": normalized,
                "label": INFERENCE_MODES[normalized],
                "model_status": state["model_status"],
            },
        )

    return app


def normalize_inference_mode(mode: str) -> str:
    return mode if mode in INFERENCE_MODES else "mediapipe_gemma"


def frame_metadata(frame: dict[str, Any] | None) -> dict[str, Any]:
    if not frame:
        return {}
    return {
        "mime": str(frame.get("mime", "")),
        "width": int(frame.get("width", 0) or 0),
        "height": int(frame.get("height", 0) or 0),
        "bytes": len(str(frame.get("data_url", ""))),
    }


async def broadcast(subscribers: set[WebSocket], payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for ws in subscribers:
        with suppress(Exception):
            await ws.send_json(payload)
            continue
        dead.append(ws)
    for ws in dead:
        subscribers.discard(ws)


def append_bounded(items: list[Any], value: Any, limit: int = 64) -> None:
    items.append(value)
    del items[:-limit]


def tailscale_ip() -> str | None:
    try:
        import subprocess

        result = subprocess.run(["tailscale", "ip", "-4"], check=False, capture_output=True, text=True, timeout=1.5)
        ip = result.stdout.strip().splitlines()
        return ip[0] if ip else None
    except Exception:
        return None


def tailscale_dns_name() -> str | None:
    try:
        import json
        import subprocess

        result = subprocess.run(["tailscale", "status", "--json"], check=False, capture_output=True, text=True, timeout=1.5)
        if result.returncode != 0:
            return None
        name = json.loads(result.stdout).get("Self", {}).get("DNSName")
        return str(name).rstrip(".") if name else None
    except Exception:
        return None


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("edgepulse.network.server:app", host="0.0.0.0", port=8501, reload=False)
