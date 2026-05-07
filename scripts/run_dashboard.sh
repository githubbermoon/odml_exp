#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
set -a
[ -f .env ] && source .env
set +a

streamlit run edgepulse/dashboard/app.py --server.address 0.0.0.0 --server.port 8501
