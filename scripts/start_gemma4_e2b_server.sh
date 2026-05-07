#!/usr/bin/env bash
set -euo pipefail

LITERT_LM_BIN="${LITERT_LM_BIN:-$HOME/.local/bin/litert-lm}"
GEMMA4_E2B_REPO="${GEMMA4_E2B_REPO:-litert-community/gemma-4-E2B-it-litert-lm}"
GEMMA4_E2B_MODEL="${GEMMA4_E2B_MODEL:-gemma-4-E2B-it.litertlm}"
GEMMA4_E2B_MODEL_ID="${GEMMA4_E2B_MODEL_ID:-gemma-4-e2b}"
GEMMA4_E2B_SERVER_HOST="${GEMMA4_E2B_SERVER_HOST:-127.0.0.1}"
GEMMA4_E2B_SERVER_PORT="${GEMMA4_E2B_SERVER_PORT:-9379}"

if ! "$LITERT_LM_BIN" list | awk '{print $1}' | grep -qx "$GEMMA4_E2B_MODEL_ID"; then
  "$LITERT_LM_BIN" import \
    --from-huggingface-repo "$GEMMA4_E2B_REPO" \
    "$GEMMA4_E2B_MODEL" \
    "$GEMMA4_E2B_MODEL_ID"
fi

exec "$LITERT_LM_BIN" serve \
  --host "$GEMMA4_E2B_SERVER_HOST" \
  --port "$GEMMA4_E2B_SERVER_PORT" \
  --api openai
