#!/bin/bash
# MycoBrain Gateway Jetson Router - Install script
# Run from MAS repo root: ./deploy/jetson-gateway/install.sh
# Or: ./deploy/jetson-gateway/install.sh /path/to/mycosoft-mas

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "${1:-}" ]]; then
    REPO_ROOT="$(cd "$1" && pwd)"
fi

INSTALL_DIR=/opt/mycobrain
VENV_DIR=${INSTALL_DIR}/venv
SERVICE_NAME=mycobrain-gateway

echo "Installing MycoBrain Gateway Router..."
echo "  Repo: $REPO_ROOT"
echo "  Install dir: $INSTALL_DIR"

# Create install directory and copy repo (or use existing)
sudo mkdir -p "$INSTALL_DIR"
if [[ ! -d "$INSTALL_DIR/mycosoft-mas" ]]; then
    echo "Copying MAS repo to $INSTALL_DIR/mycosoft-mas..."
    sudo cp -a "$REPO_ROOT" "$INSTALL_DIR/mycosoft-mas"
else
    echo "Updating existing $INSTALL_DIR/mycosoft-mas..."
    sudo rsync -a --exclude='.git' --exclude='__pycache__' "$REPO_ROOT/" "$INSTALL_DIR/mycosoft-mas/"
fi

# Create venv and install deps (share venv with ondevice if both on same host)
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtualenv at $VENV_DIR..."
    sudo python3 -m venv "$VENV_DIR"
fi
sudo "$VENV_DIR/bin/pip" install --upgrade pip
sudo "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/mycosoft-mas/deploy/jetson-gateway/requirements.txt"
sudo "$VENV_DIR/bin/pip" install -e "$INSTALL_DIR/mycosoft-mas"

# Create mycosoft user if missing
id -u mycosoft &>/dev/null || sudo useradd -r -s /bin/false mycosoft
sudo chown -R mycosoft:mycosoft "$INSTALL_DIR"

# Install env file
sudo mkdir -p /etc/mycobrain
if [[ ! -f /etc/mycobrain/gateway.env ]]; then
    echo "Creating /etc/mycobrain/gateway.env from env.gateway"
    sudo cp "$INSTALL_DIR/mycosoft-mas/deploy/jetson-gateway/env.gateway" /etc/mycobrain/gateway.env
    echo "  Edit /etc/mycobrain/gateway.env to set GATEWAY_ID and URLs"
fi

# Install systemd unit
echo "Installing systemd unit..."
sudo cp "$INSTALL_DIR/mycosoft-mas/deploy/jetson-gateway/mycobrain-gateway.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Done. Status:"
sudo systemctl status "$SERVICE_NAME" --no-pager || true
echo ""
echo "Health:  curl http://localhost:8003/health"
echo "Devices: curl http://localhost:8003/devices"
echo "Logs:    journalctl -u $SERVICE_NAME -f"
