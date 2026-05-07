from __future__ import annotations

import os
import time

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("EDGEPULSE_API_URL", "http://127.0.0.1:8501")


st.set_page_config(page_title="EdgePulse", page_icon="pulse", layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; max-width: 1480px; }
      [data-testid="stMetricValue"] { font-size: 1.45rem; }
      .pulse-card {
        border: 1px solid #263241;
        border-radius: 8px;
        padding: 14px 16px;
        background: #101820;
      }
      .hint { color: #75e6b0; font-weight: 650; }
      .reason { color: #dbeafe; }
      .small { color: #93a4b8; font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_state() -> dict:
    try:
        return requests.get(f"{API_URL}/state", timeout=0.5).json()
    except Exception as exc:
        return {"events": [], "hints": [], "reasoning": [], "latency": [], "error": str(exc)}


def post_demo_event(payload: dict) -> None:
    requests.post(f"{API_URL}/events", json=payload, timeout=1.0)


st.title("EdgePulse")
st.caption("On-device Gemma 4 showcase: MediaPipe/ODML perception with LiteRT-LM reasoning over Tailscale.")

state = fetch_state()
if "error" in state:
    st.error(f"Runtime unavailable at {API_URL}: {state['error']}")

latest_event = state.get("events", [{}])[-1] if state.get("events") else {}
latest_hint = state.get("hints", [{}])[-1] if state.get("hints") else {}
latest_reasoning = state.get("reasoning", [{}])[-1] if state.get("reasoning") else {}
latest_latency = state.get("latency", [{}])[-1] if state.get("latency") else {}

top = st.columns([1.2, 1, 1, 1])
top[0].metric("Runtime", "offline/local", state.get("mode", "mac-local"))
top[1].metric("Speculative", f"{latest_latency.get('speculative_ms', 0):.1f} ms")
top[2].metric("Reasoning", f"{latest_latency.get('reasoning_ms', 0):.0f} ms")
top[3].metric("Tailscale", state.get("tailscale_ip") or "not detected")

left, mid, right = st.columns([1.05, 1, 1])

with left:
    st.subheader("Live Perception")
    st.markdown(
        f"""
        <div class="pulse-card">
          <div class="small">Latest semantic event</div>
          <h3>{latest_event.get("gesture", "waiting")}</h3>
          <p>attention: <b>{latest_event.get("attention", "unknown")}</b></p>
          <p>head pose: <b>{latest_event.get("head_pose", "unknown")}</b></p>
          <p>duration: <b>{latest_event.get("duration", 0):.2f}s</b></p>
          <p>source: <b>{latest_event.get("source", "none")}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("Demo event injector")
    demo_cols = st.columns(3)
    if demo_cols[0].button("Raised hand"):
        post_demo_event({"source": "dashboard-demo", "gesture": "raised_hand", "attention": "focused", "duration": 5.2, "head_pose": "tilted_left", "intent_signal": "audience_question", "context": "on_device_gemma4_showcase", "confidence": 0.88})
    if demo_cols[1].button("Pointing"):
        post_demo_event({"source": "dashboard-demo", "gesture": "pointing", "attention": "focused", "duration": 2.1, "head_pose": "center", "intent_signal": "inspect_on_device_pipeline", "context": "on_device_gemma4_showcase", "confidence": 0.8})
    if demo_cols[2].button("Confused"):
        post_demo_event({"source": "dashboard-demo", "gesture": "none", "attention": "confused", "duration": 7.4, "head_pose": "tilted_right", "intent_signal": "explain_odml_stack", "context": "on_device_gemma4_showcase", "confidence": 0.73})

with mid:
    st.subheader("Speculative Interaction")
    st.markdown(
        f"""
        <div class="pulse-card">
          <div class="small">Instant drafter-style UX response</div>
          <h3 class="hint">{latest_hint.get("text", "Waiting for perception...")}</h3>
          <p>predicted intent: <b>{latest_hint.get("intent", "unknown")}</b></p>
          <p>confidence: <b>{latest_hint.get("confidence", 0):.2f}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if latest_reasoning.get("token_trace"):
        st.write("Token stream")
        st.code(" ".join(latest_reasoning["token_trace"][-16:]), language="json")

with right:
    st.subheader("Gemma Reasoning")
    st.markdown(
        f"""
        <div class="pulse-card">
          <div class="small">Refined local reasoning</div>
          <h3 class="reason">{latest_reasoning.get("intent", "waiting")}</h3>
          <p>{latest_reasoning.get("assistance", "No reasoning result yet.")}</p>
          <p>intervene: <b>{latest_reasoning.get("should_intervene", False)}</b></p>
          <p>model: <b>{latest_reasoning.get("model", "Gemma/LiteRT-LM adapter")}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Event Timeline")
events = state.get("events", [])
if events:
    st.dataframe(pd.DataFrame(events)[["source", "gesture", "attention", "head_pose", "duration", "confidence", "ts"]].tail(12), use_container_width=True)
else:
    st.info("Start the runtime, run Mac perception, or use demo event buttons.")

st.subheader("Latency Trace")
latency = state.get("latency", [])
if latency:
    df = pd.DataFrame(latency).tail(24)
    st.line_chart(df[["speculative_ms", "reasoning_ms"]])
else:
    st.caption("Latency will appear after the first event.")

time.sleep(float(os.getenv("EDGEPULSE_REFRESH_SECONDS", "0.8")))
st.rerun()
