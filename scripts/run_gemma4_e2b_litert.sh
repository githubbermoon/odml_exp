#!/usr/bin/env bash
set -euo pipefail

LITERT_LM_BIN="${LITERT_LM_BIN:-$HOME/.local/bin/litert-lm}"
GEMMA4_E2B_REPO="${GEMMA4_E2B_REPO:-litert-community/gemma-4-E2B-it-litert-lm}"
GEMMA4_E2B_MODEL="${GEMMA4_E2B_MODEL:-gemma-4-E2B-it.litertlm}"
GEMMA4_E2B_MODEL_ID="${GEMMA4_E2B_MODEL_ID:-gemma-4-e2b}"
GEMMA4_E2B_BACKEND="${GEMMA4_E2B_BACKEND:-gpu}"
GEMMA4_E2B_SPECULATIVE="${GEMMA4_E2B_SPECULATIVE:-true}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3.11 || command -v python3 || command -v python)}"

prompt="$(cat)"

MODEL_REF="$GEMMA4_E2B_MODEL_ID"
if ! "$LITERT_LM_BIN" list | awk '{print $1}' | grep -qx "$GEMMA4_E2B_MODEL_ID"; then
  MODEL_REF="$GEMMA4_E2B_MODEL"
fi

run_args=(run "$MODEL_REF" --backend="$GEMMA4_E2B_BACKEND" --enable-speculative-decoding="$GEMMA4_E2B_SPECULATIVE")
if [ "$MODEL_REF" = "$GEMMA4_E2B_MODEL" ]; then
  run_args=(run --from-huggingface-repo "$GEMMA4_E2B_REPO" "$MODEL_REF" --backend="$GEMMA4_E2B_BACKEND" --enable-speculative-decoding="$GEMMA4_E2B_SPECULATIVE")
fi

if [ -n "${EDGEPULSE_LITERT_SERVER_URL:-}" ]; then
  EDGEPULSE_PROMPT="$prompt" "$PYTHON_BIN" - "$EDGEPULSE_LITERT_SERVER_URL" "$GEMMA4_E2B_MODEL_ID" <<'PY'
import http.client
import json
import os
import sys
from urllib.parse import urlparse

url = urlparse(sys.argv[1])
model_id = sys.argv[2]
body = json.dumps({
    "model": model_id,
    "input": os.environ["EDGEPULSE_PROMPT"],
    "stream": True,
})

conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=180)
conn.request("POST", "/v1/responses", body=body, headers={"Content-Type": "application/json"})
response = conn.getresponse()
if response.status >= 400:
    sys.stdout.write(json.dumps({
        "intent": "runtime_error",
        "should_intervene": True,
        "assistance": f"LiteRT-LM server returned HTTP {response.status}: {response.read(320).decode('utf-8', errors='replace')}",
        "confidence": 0.2,
        "actions": ["check_litert_lm_server"],
    }))
    sys.exit(0)

buffer = ""
while True:
    chunk = response.read(1)
    if not chunk:
        break
    buffer += chunk.decode("utf-8", errors="replace")
    while "\n\n" in buffer:
        event, buffer = buffer.split("\n\n", 1)
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                sys.exit(0)
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            text = payload.get("delta", {}).get("text", "")
            if text:
                sys.stdout.write(text)
                sys.stdout.flush()
PY
  exit 0
fi

exec "$LITERT_LM_BIN" "${run_args[@]}" \
  --prompt "$prompt"
