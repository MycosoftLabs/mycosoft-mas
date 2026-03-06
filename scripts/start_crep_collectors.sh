#!/bin/bash
# start_crep_collectors.sh - Start CREP Gateway on MAS VM (188)
# Mar 5, 2026. Run on MAS VM after website repo is present.
#
# CREP Gateway: FastAPI at port 3020, provides /api/intel/air, maritime, fishing.
# Expects website repo at /opt/mycosoft/website or $CREP_GATEWAY_DIR.

set -e

CREP_DIR="${CREP_GATEWAY_DIR:-/opt/mycosoft/website/services/crep-gateway}"
PORT="${CREP_PORT:-3020}"
PIDFILE="/tmp/crep_gateway.pid"

if [ ! -d "$CREP_DIR" ]; then
    echo "CREP gateway dir not found: $CREP_DIR"
    echo "Set CREP_GATEWAY_DIR or deploy website repo to /opt/mycosoft/website"
    exit 1
fi

cd "$CREP_DIR"

if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "CREP gateway already running (PID $OLD_PID)"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

# Ensure deps (website repo may use different venv)
export PYTHONPATH="$CREP_DIR:$PYTHONPATH"
if command -v uvicorn &>/dev/null; then
    UVICORN=uvicorn
elif [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/uvicorn" ]; then
    UVICORN="$VIRTUAL_ENV/bin/uvicorn"
else
    UVICORN="python -m uvicorn"
fi

echo "Starting CREP gateway on port $PORT..."
nohup $UVICORN main:app --host 0.0.0.0 --port "$PORT" > /var/log/crep_gateway.log 2>&1 &
echo $! > "$PIDFILE"
echo "CREP gateway started (PID $(cat $PIDFILE)). Log: /var/log/crep_gateway.log"
echo "Health: curl http://localhost:$PORT/health"
