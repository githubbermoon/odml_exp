#!/usr/bin/env bash
set -euo pipefail

LITERT_LM_BIN="${LITERT_LM_BIN:-$HOME/.local/bin/litert-lm}"
GEMMA4_E2B_REPO="${GEMMA4_E2B_REPO:-litert-community/gemma-4-E2B-it-litert-lm}"
GEMMA4_E2B_MODEL="${GEMMA4_E2B_MODEL:-gemma-4-E2B-it.litertlm}"
GEMMA4_E2B_MODEL_ID="${GEMMA4_E2B_MODEL_ID:-gemma-4-e2b}"
GEMMA4_E2B_BACKEND="${GEMMA4_E2B_BACKEND:-gpu}"
GEMMA4_E2B_VISION_BACKEND="${GEMMA4_E2B_VISION_BACKEND:-gpu}"
GEMMA4_E2B_SPECULATIVE="${GEMMA4_E2B_SPECULATIVE:-true}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3.11 || command -v python3 || command -v python)}"

payload="$(cat)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

parsed="$(
  PAYLOAD="$payload" TMPDIR_FOR_FRAME="$tmp_dir" "$PYTHON_BIN" - <<'PY'
import base64
import json
import os
from pathlib import Path

payload = json.loads(os.environ["PAYLOAD"])
prompt = str(payload.get("prompt", ""))
frame = payload.get("frame") or {}
data_url = str(frame.get("data_url", ""))
tmp_dir = Path(os.environ.get("TMPDIR_FOR_FRAME", "."))
mime = str(frame.get("mime", "image/jpeg"))
suffix = ".png" if mime == "image/png" else ".jpg"
image_path = tmp_dir / f"edgepulse-frame{suffix}"

if "," in data_url:
    data_url = data_url.split(",", 1)[1]
if data_url:
    image_path.write_bytes(base64.b64decode(data_url))

print(json.dumps({"prompt": prompt, "image_path": str(image_path) if data_url else ""}))
PY
)"

prompt="$(printf '%s' "$parsed" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["prompt"])')"
image_path="$(printf '%s' "$parsed" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["image_path"])')"

if [ -z "$image_path" ]; then
  printf '{"intent":"missing_frame","should_intervene":true,"assistance":"Gemma Vision mode did not receive a camera frame.","confidence":0.2,"actions":["retry_analyze_frame"]}\n'
  exit 0
fi

MODEL_REF="$GEMMA4_E2B_MODEL_ID"
if ! "$LITERT_LM_BIN" list | awk '{print $1}' | grep -qx "$GEMMA4_E2B_MODEL_ID"; then
  MODEL_REF="$GEMMA4_E2B_MODEL"
fi

run_args=(run "$MODEL_REF" --backend="$GEMMA4_E2B_BACKEND" --vision-backend="$GEMMA4_E2B_VISION_BACKEND" --enable-speculative-decoding="$GEMMA4_E2B_SPECULATIVE")
if [ "$MODEL_REF" = "$GEMMA4_E2B_MODEL" ]; then
  run_args=(run --from-huggingface-repo "$GEMMA4_E2B_REPO" "$MODEL_REF" --backend="$GEMMA4_E2B_BACKEND" --vision-backend="$GEMMA4_E2B_VISION_BACKEND" --enable-speculative-decoding="$GEMMA4_E2B_SPECULATIVE")
fi

exec "$LITERT_LM_BIN" "${run_args[@]}" \
  --attachment "$image_path" \
  --prompt "$prompt"
