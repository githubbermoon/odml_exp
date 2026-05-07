#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
set -a
[ -f .env ] && source .env
set +a

python -m uvicorn edgepulse.network.server:app --host 127.0.0.1 --port 8501
