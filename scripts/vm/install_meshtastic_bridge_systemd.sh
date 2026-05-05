#!/usr/bin/env bash
# Run on MQTT broker VM (192.168.0.196) as a user with sudo, from MAS repo root.
# Usage: ./scripts/vm/install_meshtastic_bridge_systemd.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "REPO_ROOT=$REPO_ROOT"
if [[ ! -f "$REPO_ROOT/scripts/vm/mqtt-meshtastic-bridge.service" ]]; then
  echo "missing service template" >&2
  exit 1
fi
echo "Create /etc/mycosoft and install env from example (edit secrets after):"
echo "  sudo install -d /etc/mycosoft"
echo "  sudo cp $REPO_ROOT/scripts/vm/meshtastic-bridge.env.example /etc/mycosoft/meshtastic-bridge.env"
echo "  sudo chmod 600 /etc/mycosoft/meshtastic-bridge.env"
echo "Edit WorkingDirectory/ExecStart in service if your home path differs, then:"
echo "  sudo cp $REPO_ROOT/scripts/vm/mqtt-meshtastic-bridge.service /etc/systemd/system/mqtt-meshtastic-bridge.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now mqtt-meshtastic-bridge"
echo "  journalctl -u mqtt-meshtastic-bridge -f"
