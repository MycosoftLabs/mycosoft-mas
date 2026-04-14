#!/usr/bin/env bash
# Run on Earth-2 Legion (WSL). Called from Start-LegionEarth2API-24x7.ps1 or systemd.
set -euo pipefail
export EARTH2_API_HOST="${EARTH2_API_HOST:-0.0.0.0}"
export EARTH2_API_PORT="${EARTH2_API_PORT:-8220}"
REPO="${MYCOSOFT_EARTH2_REPO:-/root/mycosoft-mas}"
PY="${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python}"
LOG="${REPO}/earth2-api-nohup.log"
cd "$REPO"
exec "$PY" scripts/earth2_api_server.py >>"$LOG" 2>&1
