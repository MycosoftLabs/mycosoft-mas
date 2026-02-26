#!/bin/bash
# MAS Health Watchdog - restart container if health fails
# Run via cron every 5 min: */5 * * * * /home/mycosoft/mycosoft/mas/scripts/mas_watchdog.sh

HEALTH_URL="http://127.0.0.1:8001/health"
CONTAINER="myca-orchestrator-new"
LOG="/home/mycosoft/mas_watchdog.log"

if curl -sf -m 15 "$HEALTH_URL" >/dev/null 2>&1; then
  echo "$(date +%Y-%m-%dT%H:%M:%S) OK" >> "$LOG" 2>/dev/null || true
  exit 0
fi

echo "$(date +%Y-%m-%dT%H:%M:%S) FAIL - restarting $CONTAINER" >> "$LOG"
docker restart "$CONTAINER" >> "$LOG" 2>&1
exit 0
