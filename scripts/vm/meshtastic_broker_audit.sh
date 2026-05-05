#!/usr/bin/env bash
# Run ON broker VM 192.168.0.196 (ssh mycosoft@192.168.0.196). Read-only audit helpers.
set -euo pipefail
echo "=== mosquitto ==="
systemctl is-active mosquitto 2>/dev/null || true
echo "=== listeners 1883 9001 ==="
ss -lntp 2>/dev/null | grep -E ':1883|:9001' || true
echo "=== meshtastic bridge unit (if installed) ==="
systemctl is-active mqtt-meshtastic-bridge 2>/dev/null || echo "unit_not_installed"
echo "=== processes matching bridge ==="
ps aux | grep -E 'mqtt_meshtastic_bridge|meshtastic_bridge' | grep -v grep || true
