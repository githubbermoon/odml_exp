#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
set -a
[ -f .env ] && source .env
set +a

python -m edgepulse.run_perception
