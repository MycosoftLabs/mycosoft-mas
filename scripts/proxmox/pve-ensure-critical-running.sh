#!/bin/bash
# Run on Proxmox VE node as root via cron every 5 minutes OR systemd timer.
# Starts production guests if they are stopped (crash, mistaken shutdown, dependency order).
#
# Cron example (root crontab: crontab -e):
#   */5 * * * * /usr/local/sbin/pve-ensure-critical-running.sh >> /var/log/pve-ensure-critical.log 2>&1
#
# Install:
#   sudo cp pve-ensure-critical-running.sh /usr/local/sbin/
#   sudo chmod +x /usr/local/sbin/pve-ensure-critical-running.sh

set -uo pipefail

IDS=()
if [[ -n "${CRITICAL_VMIDS:-}" ]]; then
  read -ra IDS <<< "${CRITICAL_VMIDS}"
elif [[ -f /etc/mycosoft/pve-critical-vmids ]]; then
  # One VMID per line; # comments allowed
  while read -r line || [[ -n "${line:-}" ]]; do
    [[ -z "${line// }" || "$line" =~ ^# ]] && continue
    IDS+=("$line")
  done < /etc/mycosoft/pve-critical-vmids
elif [[ $# -gt 0 ]]; then
  IDS=("$@")
else
  echo "Set CRITICAL_VMIDS, create /etc/mycosoft/pve-critical-vmids, or pass VMIDs as args."
  exit 1
fi

for vmid in "${IDS[@]}"; do
  if ! qm status "$vmid" &>/dev/null; then
    logger -t pve-ensure "WARN: VM $vmid not found — skip"
    continue
  fi
  st=""
  st=$(qm status "$vmid" 2>/dev/null | awk '{print $2}')
  if [[ "$st" == "stopped" ]]; then
    logger -t pve-ensure "Starting stopped production VM $vmid"
    qm start "$vmid" || logger -t pve-ensure "FAILED to start VM $vmid"
  fi
done
