#!/usr/bin/env bash
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found. Install Tailscale first."
  exit 1
fi

echo "Starting Tailscale HTTPS serve for EdgePulse..."
echo "Run ./scripts/run_pwa.sh in another terminal first."
tailscale serve --bg http://127.0.0.1:8501
tailscale serve status
