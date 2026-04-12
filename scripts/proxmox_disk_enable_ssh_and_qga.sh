#!/usr/bin/env bash
# Run ON Proxmox host as root. VM must be stopped.
# Enables SSH password auth + installs qemu-guest-agent in guest disk (VMID from env, default 101).
set -euo pipefail
VMID="${MQTT_VM_VMID:-101}"
DISK="/dev/pve/vm-${VMID}-disk-0"
if ! [[ -b "$DISK" ]]; then
  echo "ERROR: block device not found: $DISK"
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq libguestfs-tools

# Cloud images often set PasswordAuthentication no in the MAIN sshd_config AFTER
# Include sshd_config.d/*, so a drop-in alone does not enable password login.
virt-customize -a "$DISK" \
  --install qemu-guest-agent \
  --run-command 'systemctl enable qemu-guest-agent' \
  --run-command 'install -d /etc/ssh/sshd_config.d' \
  --run-command 'printf "%s\n" "PasswordAuthentication yes" "KbdInteractiveAuthentication yes" > /etc/ssh/sshd_config.d/99-mqtt-bootstrap.conf' \
  --run-command "sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config" \
  --run-command "sed -i 's/^#\\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication yes/' /etc/ssh/sshd_config" \
  --run-command "grep -q '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config" \
  --run-command "grep -q '^KbdInteractiveAuthentication' /etc/ssh/sshd_config || echo 'KbdInteractiveAuthentication yes' >> /etc/ssh/sshd_config"

echo "Disk $DISK updated (qemu-guest-agent + SSH password auth)."
