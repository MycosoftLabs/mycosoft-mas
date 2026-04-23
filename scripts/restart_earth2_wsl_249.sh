#!/usr/bin/env bash
# Run ON Earth-2 Legion WSL (Ubuntu) as root — restart Earth-2 API on 8220.
set -eu
export UVICORN_LOOP=asyncio
export EARTH2_API_HOST=0.0.0.0
export EARTH2_API_PORT=8220
REPO=/root/mycosoft-mas
PY="${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python}"
cd "$REPO"
pkill -f earth2_api_server.py 2>/dev/null || true
fuser -k 8220/tcp 2>/dev/null || true
sleep 2
nohup env UVICORN_LOOP=asyncio EARTH2_API_HOST=0.0.0.0 EARTH2_API_PORT=8220 \
  MYCOSOFT_EARTH2_REPO="$REPO" MYCOSOFT_EARTH2_PYTHON="$PY" \
  bash scripts/gpu-node/wsl/run-earth2-api-daemon.sh </dev/null >>"$REPO/earth2-restart-cursor.log" 2>&1 &
sleep 12
curl -sS -m 20 http://127.0.0.1:8220/health || { echo "health_fail"; exit 1; }
echo ""
curl -sS -m 10 http://127.0.0.1:8220/health/event_loop 2>/dev/null || true
