#!/bin/bash
# Fix browsers not opening on Jetson Orin (Snap 2.70 incompatibility)
# Root cause: Snap 2.70 requires CONFIG_SQUASHFS_XATTR; stock Jetson kernel lacks it.
# See: https://jetsonhacks.com/2025/07/12/why-chromium-suddenly-broke-on-jetson-orin-and-how-to-bring-it-back/
#
# Strategy:
#   1. Try snap revert (instant if cached)
#   2. Try snap downgrade to 2.68.5
#   3. Install Chromium via Flatpak (works regardless of snap)
# Run as: sudo bash fix_jetson_browsers.sh

set -e

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)"
REAL_HOME="${REAL_HOME:-/home/jetson}"

echo "=== Jetson Browser Fix (Snap 2.70 / Flatpak) ==="
echo "Target user: $REAL_USER ($REAL_HOME)"
echo ""

# FLATPAK_ONLY=1 skips snap steps and goes straight to Flatpak + Epiphany
SKIP_SNAP="${FLATPAK_ONLY:-0}"
if [ "$SKIP_SNAP" = "1" ]; then
  echo "FLATPAK_ONLY=1: skipping snap steps, installing Flatpak Chromium directly."
  echo ""
else
  # Diagnose: capture error when launching Chromium
  echo "--- Diagnosing ---"
  if command -v chromium-browser &>/dev/null || command -v chromium &>/dev/null; then
    BROWSER_CMD="chromium-browser 2>&1 || chromium 2>&1"
    echo "Testing Chromium launch (5s timeout)..."
    timeout 5 bash -c "$BROWSER_CMD" 2>&1 | head -20 || true
  fi

  # 1. Try snap revert (fastest if an older snapd is cached)
# Note: 2.70+ breaks on Jetson; only exit if reverted to < 2.70
echo ""
echo "--- Step 1: Snap revert ---"
SNAP_GOOD=0
if snap list snapd &>/dev/null 2>&1; then
  if sudo snap revert snapd 2>/dev/null; then
    echo "Snap reverted successfully."
    sudo snap refresh --hold snapd 2>/dev/null || true
    echo "Held snapd to prevent auto-update."
    SNAP_VER=$(snap list snapd 2>/dev/null | awk '$1=="snapd"{print $2}' | head -1)
    if [ -n "$SNAP_VER" ]; then
      MAJOR=$(echo "$SNAP_VER" | cut -d. -f1)
      MINOR=$(echo "$SNAP_VER" | cut -d. -f2)
      if [ "${MAJOR:-99}" -lt 2 ] || { [ "${MAJOR:-0}" -eq 2 ] && [ "${MINOR:-99}" -lt 70 ]; }; then
        SNAP_GOOD=1
      fi
    fi
    if [ "$SNAP_GOOD" = "1" ]; then
      echo "Snapd version $SNAP_VER is compatible. Reboot may help: sudo reboot"
      echo "=== Done (snap revert) ==="
      exit 0
    fi
    echo "Snapd reverted to $SNAP_VER (still 2.70+); proceeding to Flatpak..."
  else
    echo "Snap revert not available (no cached revision)."
  fi
else
  echo "Snap not present or not working."
fi

# 2. Try snap downgrade to 2.68.5 (revision 24724)
echo ""
echo "--- Step 2: Snap downgrade to 2.68.5 ---"
SNAPD_REV=24724
cd /tmp
if snap download snapd --revision=$SNAPD_REV 2>/dev/null; then
  if [ -f snapd_${SNAPD_REV}.assert ] && [ -f snapd_${SNAPD_REV}.snap ]; then
    sudo snap ack snapd_${SNAPD_REV}.assert
    sudo snap install snapd_${SNAPD_REV}.snap
    sudo snap refresh --hold snapd
    echo "Snap downgraded to 2.68.5 and held."
    rm -f snapd_${SNAPD_REV}.assert snapd_${SNAPD_REV}.snap
    echo "Reboot recommended: sudo reboot"
    echo "=== Done (snap downgrade) ==="
    exit 0
  fi
  rm -f snapd_${SNAPD_REV}.assert snapd_${SNAPD_REV}.snap 2>/dev/null || true
fi
echo "Snap downgrade skipped or failed."
fi

# 3. Install Chromium via Flatpak (works regardless of snap)
echo ""
echo "--- Step 3: Install Chromium via Flatpak ---"
sudo apt-get update
sudo apt-get install -y flatpak

# Add Flathub (use correct URL for ARM64)
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true

# Install Chromium (Flathub has org.chromium.Chromium for aarch64)
echo "Installing Chromium from Flathub (this may take a few minutes)..."
if flatpak install -y flathub org.chromium.Chromium 2>/dev/null; then
  echo "Flatpak Chromium installed."
  # Create desktop shortcut so it appears in applications
  mkdir -p "$REAL_HOME/Desktop"
  cat > "$REAL_HOME/Desktop/chromium.desktop" << 'DESKTOP'
[Desktop Entry]
Name=Chromium
Comment=Web Browser
Exec=flatpak run org.chromium.Chromium %U
Icon=org.chromium.Chromium
Type=Application
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;
DESKTOP
  chown "$REAL_USER:$REAL_USER" "$REAL_HOME/Desktop/chromium.desktop"
  chmod +x "$REAL_HOME/Desktop/chromium.desktop"
  echo "Desktop shortcut: $REAL_HOME/Desktop/chromium.desktop"
else
  echo "Flatpak Chromium install failed. Trying Firefox..."
  flatpak install -y flathub org.mozilla.firefox 2>/dev/null || true
fi

# 4. Fallback: Epiphany (GNOME Web) from apt - not a snap, often works
echo ""
echo "--- Step 4: Fallback - Epiphany (apt) ---"
sudo apt-get install -y epiphany-browser 2>/dev/null || true

# 5. Chromium wrapper: when Cursor or other apps run "chromium", launch Epiphany instead
#    This fixes the "wheel spin, no browser window" issue - Cursor invokes chromium, which fails; wrapper uses Epiphany
echo ""
echo "--- Step 5: Chromium wrapper (redirects to Epiphany) ---"
WRAPPER='#!/bin/bash
# Chromium wrapper - snap Chromium broken on Jetson; use Epiphany
exec epiphany-browser "$@"'
echo "$WRAPPER" | sudo tee /usr/local/bin/chromium >/dev/null
echo "$WRAPPER" | sudo tee /usr/local/bin/chromium-browser >/dev/null
sudo chmod +x /usr/local/bin/chromium /usr/local/bin/chromium-browser 2>/dev/null || true
echo "Created /usr/local/bin/chromium and chromium-browser -> Epiphany"

echo ""
echo "=== Done ==="
echo "Try: flatpak run org.chromium.Chromium   (or Epiphany from Applications)"
echo "chromium / chromium-browser now launches Epiphany (fixes Cursor sign-in)."
echo "A reboot may be needed: sudo reboot"
echo "Cursor sign-in uses an embedded browser; once Chromium/Epiphany works, Cursor should too."
