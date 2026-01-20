#!/usr/bin/env bash
set -euo pipefail

NAS_HOST="192.168.0.105"
SMB_SHARE="mycosoft.com"
SMB_USER_DEFAULT="morgan@mycosoft.org"

MOUNT_ROOT="/mnt/mycosoft-nas"
TARGET="/opt/mycosoft/media/website/assets"
CREDS="/etc/samba/mycosoft-nas.creds"
FSTAB_MARKER="# mycosoft-nas-assets"

function print_cifs_dmesg_tail() {
  echo ""
  echo "=== CIFS kernel logs (tail) ==="
  # Keep this intentionally small to avoid hanging.
  sudo dmesg -T 2>/dev/null | egrep -i 'cifs|smb|mount\.cifs|STATUS_' | tail -n 80 || true
  echo "=== end ==="
  echo ""
}

function try_mount_root_share() {
  local opts="$1"
  echo "Trying: mount -t cifs //${NAS_HOST}/${SMB_SHARE} ${MOUNT_ROOT} -o ${opts}"
  sudo umount "$MOUNT_ROOT" 2>/dev/null || true
  if sudo mount -t cifs "//${NAS_HOST}/${SMB_SHARE}" "$MOUNT_ROOT" -o "${opts}"; then
    echo "[OK] CIFS mount succeeded with: ${opts}"
    return 0
  fi
  echo "[FAIL] CIFS mount failed with: ${opts}"
  print_cifs_dmesg_tail
  return 1
}

echo "[1/9] Installing cifs-utils"
sudo apt-get update -y
sudo apt-get install -y cifs-utils

echo "[2/9] Creating mountpoints"
sudo mkdir -p "$MOUNT_ROOT" "$TARGET"
sudo install -d -m 0700 /etc/samba

echo "[3/9] SMB credentials (entered on VM; never stored in chat)"
read -rp "NAS SMB username [${SMB_USER_DEFAULT}] (or type 'guest'): " SMB_USER_INPUT
SMB_USER="${SMB_USER_INPUT:-$SMB_USER_DEFAULT}"
unset SMB_USER_INPUT

if [ "$SMB_USER" = "guest" ]; then
  echo "[INFO] Using guest SMB mode (no credentials file)."
  USE_GUEST="true"
else
  USE_GUEST="false"
  read -rsp "NAS SMB password for ${SMB_USER}: " SMB_PASS
  echo
  printf "username=%s\npassword=%s\n" "$SMB_USER" "$SMB_PASS" | sudo tee "$CREDS" >/dev/null
  unset SMB_PASS
  sudo chmod 600 "$CREDS"
fi

echo "[4/9] Test-mount SMB share (do NOT write fstab until this succeeds)"

# Options notes:
# - sec=ntlmssp is the most common fix for mount error(13) with modern SMB/NAS auth setups.
# - noserverino avoids inode issues seen on some NAS implementations.
# - nounix helps when the server doesn't support Unix extensions correctly.
if [ "$USE_GUEST" = "true" ]; then
  MOUNT_OPTS_BASE="guest,iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755,nofail,_netdev"
else
  MOUNT_OPTS_BASE="credentials=${CREDS},iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755,nofail,_netdev"
fi

if ! try_mount_root_share "${MOUNT_OPTS_BASE},vers=3.0,sec=ntlmssp,noserverino,nounix"; then
  echo "Retrying with fallback options..."
  if ! try_mount_root_share "${MOUNT_OPTS_BASE},vers=3.0,sec=ntlmssp,noserverino"; then
    if ! try_mount_root_share "${MOUNT_OPTS_BASE},vers=2.1,sec=ntlmssp,noserverino,nounix"; then
      echo ""
      echo "[FATAL] Unable to mount SMB share //${NAS_HOST}/${SMB_SHARE}"
      echo "Most common causes:"
      echo "  - Wrong username/password for SMB"
      echo "  - The SMB user does not have access to the share '${SMB_SHARE}'"
      echo "  - NAS requires a different SMB auth mode (rare), or SMB is disabled"
      echo ""
      echo "Next diagnostics to run on the VM (you will be prompted for the NAS password):"
      echo "  smbclient -L //${NAS_HOST} -U '${SMB_USER}'"
      echo "  smbclient //${NAS_HOST}/${SMB_SHARE} -U '${SMB_USER}' -c 'ls'"
      echo ""
      exit 1
    fi
  fi
fi

echo "[5/9] Verify subpath exists on the NAS share"
if [ ! -d "${MOUNT_ROOT}/website/assets" ]; then
  echo "[FATAL] The expected folder does not exist on the share:"
  echo "  ${MOUNT_ROOT}/website/assets"
  echo ""
  echo "This should correspond to:"
  echo "  \\\\${NAS_HOST}\\\\${SMB_SHARE}\\\\website\\\\assets"
  echo ""
  echo "Create it (or fix the subpath/share), then re-run this script."
  exit 1
fi

echo "[6/9] Bind-mount NAS subpath to website assets host path"
sudo umount "$TARGET" 2>/dev/null || true
sudo mount --bind "${MOUNT_ROOT}/website/assets" "$TARGET"

echo "[7/9] Persist mounts in /etc/fstab (idempotent)"
FSTAB_CIFS="//${NAS_HOST}/${SMB_SHARE} ${MOUNT_ROOT} cifs ${MOUNT_OPTS_BASE},vers=3.0,sec=ntlmssp,noserverino,nounix 0 0"
FSTAB_BIND="${MOUNT_ROOT}/website/assets ${TARGET} none bind 0 0"

sudo grep -qF "$FSTAB_MARKER" /etc/fstab || echo "$FSTAB_MARKER" | sudo tee -a /etc/fstab >/dev/null
sudo grep -qF "$FSTAB_CIFS" /etc/fstab || echo "$FSTAB_CIFS" | sudo tee -a /etc/fstab >/dev/null
sudo grep -qF "$FSTAB_BIND" /etc/fstab || echo "$FSTAB_BIND" | sudo tee -a /etc/fstab >/dev/null

echo "[8/9] Verify mounts"
mount | grep -i cifs || true
mount | grep -E "${TARGET}|${MOUNT_ROOT}" || true

echo "[9/9] Verify Mushroom1 files exist (NAS-backed) + origin serves from /assets"
ls -la "$TARGET/mushroom1" | head -n 25 || true
curl -I -s http://localhost:3000/assets/mushroom1/a.mp4 | head -n 15 || true

echo "DONE"

