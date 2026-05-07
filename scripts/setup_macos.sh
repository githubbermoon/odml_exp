#!/usr/bin/env bash
set -euo pipefail

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp -n .env.example .env || true
echo "Mac setup complete. Run 'uv tool install litert-lm' if needed, then ./scripts/run_pwa.sh."
