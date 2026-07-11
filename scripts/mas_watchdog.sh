#!/bin/bash
# MAS Health Watchdog — JUL 10 2026
# Survives Docker-only assumptions: prefers systemd mas-orchestrator, falls back to docker.
# Cron: */2 * * * * /home/mycosoft/mas_watchdog.sh
# Flap alert: after N consecutive failures, POST to MAS alert webhook if configured.

set -u
HEALTH_URL="${MAS_HEALTH_URL:-http://127.0.0.1:8001/health}"
COMPLIANCE_URL="${MAS_COMPLIANCE_HEALTH_URL:-http://127.0.0.1:8001/api/compliance/health}"
LOG="${MAS_WATCHDOG_LOG:-/home/mycosoft/mas_watchdog.log}"
STATE="${MAS_WATCHDOG_STATE:-/home/mycosoft/mas_watchdog.state}"
ALERT_URL="${MAS_WATCHDOG_ALERT_URL:-}"
FLAP_THRESHOLD="${MAS_WATCHDOG_FLAP_THRESHOLD:-3}"
SYSTEMD_UNIT="${MAS_SYSTEMD_UNIT:-mas-orchestrator}"
DOCKER_CONTAINER="${MAS_DOCKER_CONTAINER:-myca-orchestrator-new}"

ts() { date +%Y-%m-%dT%H:%M:%S; }

ok_health() {
  curl -sf -m 10 "$HEALTH_URL" >/dev/null 2>&1
}

ok_compliance() {
  # Soft check — do not restart solely for empty seed; only for hard failure of API process.
  curl -sf -m 10 "$COMPLIANCE_URL" >/dev/null 2>&1 || true
  return 0
}

read_fail_count() {
  if [[ -f "$STATE" ]]; then
    cat "$STATE" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

write_fail_count() {
  echo "$1" > "$STATE"
}

emit_flap_alert() {
  local count="$1"
  local msg="MAS watchdog: $count consecutive health failures on $(hostname) — auto-restart attempted"
  echo "$(ts) ALERT $msg" >> "$LOG"
  if [[ -n "$ALERT_URL" ]]; then
    curl -sf -m 10 -X POST "$ALERT_URL" \
      -H "Content-Type: application/json" \
      -d "{\"source\":\"mas_watchdog\",\"severity\":\"high\",\"message\":\"$msg\",\"fail_count\":$count}" \
      >> "$LOG" 2>&1 || true
  fi
  # Best-effort local MAS alert API
  curl -sf -m 10 -X POST "http://127.0.0.1:8001/api/alerts" \
    -H "Content-Type: application/json" \
    -d "{\"source\":\"mas_watchdog\",\"severity\":\"high\",\"title\":\"MAS health flap\",\"message\":\"$msg\"}" \
    >> "$LOG" 2>&1 || true
}

restart_mas() {
  if systemctl is-enabled "$SYSTEMD_UNIT" >/dev/null 2>&1 || systemctl status "$SYSTEMD_UNIT" >/dev/null 2>&1; then
    echo "$(ts) FAIL - systemctl restart $SYSTEMD_UNIT" >> "$LOG"
    # passwordless sudo preferred; fall back to docker if sudo denied
    if sudo -n systemctl restart "$SYSTEMD_UNIT" >> "$LOG" 2>&1; then
      return 0
    fi
  fi
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$DOCKER_CONTAINER"; then
    echo "$(ts) FAIL - docker restart $DOCKER_CONTAINER" >> "$LOG"
    docker restart "$DOCKER_CONTAINER" >> "$LOG" 2>&1
    return 0
  fi
  echo "$(ts) FAIL - no systemd unit and no docker container to restart" >> "$LOG"
  return 1
}

if ok_health; then
  ok_compliance
  write_fail_count 0
  echo "$(ts) OK" >> "$LOG" 2>/dev/null || true
  exit 0
fi

fails=$(read_fail_count)
fails=$((fails + 1))
write_fail_count "$fails"
echo "$(ts) FAIL count=$fails" >> "$LOG"
restart_mas
if [[ "$fails" -ge "$FLAP_THRESHOLD" ]]; then
  emit_flap_alert "$fails"
fi
exit 0
