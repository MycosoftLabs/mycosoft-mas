#!/usr/bin/env bash
set -euo pipefail

# Install systemd services for:
# - on-device operator (Jetson 16GB)
# - gateway router (Jetson 4GB)
#
# Usage:
#   sudo bash deploy/jetson/install_jetson_services.sh ondevice
#   sudo bash deploy/jetson/install_jetson_services.sh gateway

MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  echo "Usage: $0 [ondevice|gateway]"
  exit 1
fi

ROOT_DIR="/opt/mycosoft/mas"
SYSTEMD_DIR="/etc/systemd/system"
ENV_DIR="/etc/mycosoft"

mkdir -p "$ENV_DIR"

case "$MODE" in
  ondevice)
    cp "$ROOT_DIR/deploy/jetson/mycobrain-ondevice-operator.service" "$SYSTEMD_DIR/"
    if [[ ! -f "$ENV_DIR/ondevice-operator.env" ]]; then
      cp "$ROOT_DIR/deploy/jetson/ondevice-operator.env.example" "$ENV_DIR/ondevice-operator.env"
    fi
    systemctl daemon-reload
    systemctl enable mycobrain-ondevice-operator.service
    systemctl restart mycobrain-ondevice-operator.service
    systemctl --no-pager --full status mycobrain-ondevice-operator.service || true
    ;;
  gateway)
    cp "$ROOT_DIR/deploy/jetson/mycobrain-gateway-router.service" "$SYSTEMD_DIR/"
    if [[ ! -f "$ENV_DIR/gateway-router.env" ]]; then
      cp "$ROOT_DIR/deploy/jetson/gateway-router.env.example" "$ENV_DIR/gateway-router.env"
    fi
    systemctl daemon-reload
    systemctl enable mycobrain-gateway-router.service
    systemctl restart mycobrain-gateway-router.service
    systemctl --no-pager --full status mycobrain-gateway-router.service || true
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Expected: ondevice or gateway"
    exit 1
    ;;
esac

