#!/usr/bin/env bash
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found. Install Tailscale on Mac and Android, then sign both into the same tailnet."
  exit 1
fi

echo "Mac Tailscale IPv4:"
tailscale ip -4
echo
echo "Tailnet peers:"
tailscale status
