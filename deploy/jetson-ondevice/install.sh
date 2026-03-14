#!/bin/bash
# MycoBrain On-Device Jetson Operator - Install script
# Run from MAS repo root: ./deploy/jetson-ondevice/install.sh
# Or: ./deploy/jetson-ondevice/install.sh /path/to/mycosoft-mas

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "${1:-}" ]]; then
    REPO_ROOT="$(cd "$1" && pwd)"
fi

INSTALL_DIR=/opt/mycobrain
VENV_DIR=${INSTALL_DIR}/venv
SERVICE_NAME=mycobrain-operator

echo "Installing MycoBrain On-Device Operator..."
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

# Create venv and install deps
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtualenv at $VENV_DIR..."
    sudo python3 -m venv "$VENV_DIR"
fi
sudo "$VENV_DIR/bin/pip" install --upgrade pip
sudo "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/mycosoft-mas/deploy/jetson-ondevice/requirements.txt"
sudo "$VENV_DIR/bin/pip" install -e "$INSTALL_DIR/mycosoft-mas"

# Create mycosoft user if missing
id -u mycosoft &>/dev/null || sudo useradd -r -s /bin/false mycosoft
sudo chown -R mycosoft:mycosoft "$INSTALL_DIR"

# Install env file (use mushroom1 by default if not present)
sudo mkdir -p /etc/mycobrain
if [[ ! -f /etc/mycobrain/operator.env ]]; then
    echo "Creating /etc/mycobrain/operator.env from env.mushroom1 (customize as needed)"
    sudo cp "$INSTALL_DIR/mycosoft-mas/deploy/jetson-ondevice/env.mushroom1" /etc/mycobrain/operator.env
    echo "  Edit /etc/mycobrain/operator.env to set serial ports and device ID"
fi

# Install systemd unit
echo "Installing systemd unit..."
sudo cp "$INSTALL_DIR/mycosoft-mas/deploy/jetson-ondevice/mycobrain-operator.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Done. Status:"
sudo systemctl status "$SERVICE_NAME" --no-pager || true
echo ""
echo "Health: curl http://localhost:8080/health"
echo "Logs:   journalctl -u $SERVICE_NAME -f"
