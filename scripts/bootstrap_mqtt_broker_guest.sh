#!/usr/bin/env bash
# Run ON the Ubuntu MQTT guest after first boot (cloud-init).
# Mosquitto on 1883 with password auth, persistence, UFW 22+1883 only.
# Date: Apr 08, 2026
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

timedatectl set-ntp true || true
systemctl enable --now systemd-timesyncd 2>/dev/null || true

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y mosquitto mosquitto-clients ufw

install -d -o mosquitto -g mosquitto /var/lib/mosquitto
install -d -m 0755 /etc/mosquitto/conf.d

PW_FILE=/etc/mosquitto/passwd
if [[ ! -f "$PW_FILE" ]]; then
  read -r -s -p "New MQTT password for user 'mycobrain': " MQPW
  echo
  mosquitto_passwd -c -b "$PW_FILE" mycobrain "$MQPW"
  chmod 0640 "$PW_FILE"
  chown root:mosquitto "$PW_FILE"
fi

cat >/etc/mosquitto/conf.d/99-mycobrain.conf <<'EOF'
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
autosave_interval 60
EOF

systemctl enable mosquitto
systemctl restart mosquitto

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 1883/tcp comment 'MQTT'
ufw --force enable

echo "Mosquitto listening on 1883 (auth). SSH + 1883 allowed in UFW."
echo "Verify: timedatectl status"
systemctl --no-pager status mosquitto || true
