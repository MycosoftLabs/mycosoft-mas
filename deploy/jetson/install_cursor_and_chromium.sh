#!/bin/bash
# Install Cursor and Chromium on Jetson (Ubuntu/Orin)
# Run as: ./install_cursor_and_chromium.sh (sudo for apt; installs to GUI user's home)
# User: jetson (Desktop GUI user)

set -e

# When run via sudo, use the actual user's home (jetson), not /root
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)"
REAL_HOME="${REAL_HOME:-/home/jetson}"

echo "=== Jetson Cursor + Chromium Install ==="
echo "Install target: $REAL_HOME (user $REAL_USER)"

# 1. Update and install Chromium
echo "--- Installing Chromium ---"
sudo apt-get update
sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium

# 2. Cursor ARM64 AppImage (official api2.cursor.sh)
CURSOR_DIR="$REAL_HOME/.local/share/cursor"
CURSOR_APP="$CURSOR_DIR/cursor.AppImage"
mkdir -p "$CURSOR_DIR"

echo "--- Downloading Cursor (ARM64) ---"
CURSOR_URL="https://api2.cursor.sh/updates/download/golden/linux-arm64/cursor/2.6"
if curl -fsSL -o "$CURSOR_APP" "$CURSOR_URL"; then
  chmod +x "$CURSOR_APP"
  chown -R "$REAL_USER:$REAL_USER" "$CURSOR_DIR" 2>/dev/null || true
  echo "Cursor AppImage: $CURSOR_APP"
else
  echo "WARNING: Cursor download failed. Check network and URL: $CURSOR_URL"
fi

# 3. Desktop shortcut for Cursor (create Desktop if missing)
mkdir -p "$REAL_HOME/Desktop"
DESKTOP="$REAL_HOME/Desktop/cursor.desktop"
cat > "$DESKTOP" << EOF
[Desktop Entry]
Name=Cursor
Exec=$CURSOR_APP
Icon=accessories-text-editor
Type=Application
Categories=Development;TextEditor;
EOF
chown "$REAL_USER:$REAL_USER" "$DESKTOP" 2>/dev/null || true
chmod +x "$DESKTOP"
echo "Desktop shortcut: $DESKTOP"

# 4. Verify Chromium
echo "--- Verifying Chromium ---"
which chromium-browser 2>/dev/null || which chromium 2>/dev/null || echo "Chromium not in PATH"
chromium-browser --version 2>/dev/null || chromium --version 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Chromium: Start from Applications menu or: chromium-browser"
echo "Cursor:   $CURSOR_APP  (or double-click Desktop shortcut)"
echo "If Cursor fails: GLIBC/AppImage issues on Jetson are common; try running from terminal to see errors."
