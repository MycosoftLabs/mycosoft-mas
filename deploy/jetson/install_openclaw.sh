#!/usr/bin/env bash
# Install and configure OpenClaw on Jetson for on-site AI device management.
# OpenClaw Gateway serves Control UI at http://<host>:18789 and WebSocket for chat/exec.
#
# Usage:
#   bash deploy/jetson/install_openclaw.sh
#
# Prereqs: Node.js 22+ or Bun (ARM64). Run install_cursor_and_chromium.sh first for Node.
# Created: March 13, 2026

set -euo pipefail

OPENCLAW_PORT="${OPENCLAW_PORT:-18789}"
# OpenClaw uses --bind lan (0.0.0.0) or --bind loopback (127.0.0.1), not --host
OPENCLAW_BIND="${OPENCLAW_BIND:-lan}"

echo "=== OpenClaw Jetson Install ==="

# Ensure Node or Bun
if command -v bun &>/dev/null; then
  PKG_MGR="bun"
  INSTALL_CMD="bun install -g openclaw@latest"
elif command -v node &>/dev/null; then
  PKG_MGR="npm"
  INSTALL_CMD="npm install -g openclaw@latest"
else
  echo "Error: Node.js or Bun required. Run install_cursor_and_chromium.sh first."
  exit 1
fi

echo "Using $PKG_MGR. Installing OpenClaw..."
$INSTALL_CMD

echo "Installed. Verifying..."
# npm global bin may not be in PATH for this shell; use npx or explicit path
(npx --yes openclaw --version 2>/dev/null || openclaw --version 2>/dev/null) || true

# Create systemd user service for OpenClaw Gateway
# systemd user services have minimal PATH; use npx or explicit npm global bin
SERVICE_NAME="openclaw-gateway"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"
mkdir -p "$(dirname "$SERVICE_FILE")"

# Resolve openclaw to an ABSOLUTE path (systemd has minimal PATH - "openclaw" or "npx" will fail)
NPM_BIN=""
if command -v npm &>/dev/null; then
  NPM_BIN="$(npm bin -g 2>/dev/null)"
fi
OPENCLAW_EXEC=""
if [ -n "$NPM_BIN" ] && [ -x "$NPM_BIN/openclaw" ]; then
  OPENCLAW_EXEC="$NPM_BIN/openclaw"
elif command -v openclaw &>/dev/null; then
  OPENCLAW_EXEC="$(command -v openclaw)"
fi
if [ -z "$OPENCLAW_EXEC" ]; then
  # Fallback: npx with full path (NodeSource puts npx in /usr/bin)
  NPX_PATH="$(command -v npx 2>/dev/null)"
  if [ -n "$NPX_PATH" ]; then
    OPENCLAW_EXEC="$NPX_PATH openclaw"
  else
    echo "Error: Could not find openclaw or npx. npm install -g may have failed."
    exit 1
  fi
fi

# Ensure PATH includes npm global bin for systemd (minimal default PATH)
NPM_GLOBAL_BIN="${NPM_BIN:-$(npm bin -g 2>/dev/null)}"
EXTRA_PATH="${NPM_GLOBAL_BIN:+:$NPM_GLOBAL_BIN}"
ENV_PATH="/usr/bin:/bin:/usr/local/bin$EXTRA_PATH"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=OpenClaw Gateway - On-Site AI for MycoBrain
After=network.target

[Service]
Type=simple
Environment=PATH=$ENV_PATH
Environment=OPENCLAW_PORT=$OPENCLAW_PORT
ExecStart=$OPENCLAW_EXEC gateway --port $OPENCLAW_PORT --bind $OPENCLAW_BIND --allow-unconfigured
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

echo "Created systemd user service: $SERVICE_FILE"
echo "Enable and start with:"
echo "  systemctl --user daemon-reload"
echo "  systemctl --user enable $SERVICE_NAME"
echo "  systemctl --user start $SERVICE_NAME"
echo ""
echo "Control UI: http://$(hostname -I 2>/dev/null | awk '{print $1}'):$OPENCLAW_PORT/"
echo "Or from mycosoft.com Device Manager -> On-Site AI -> select device -> Open OpenClaw"
