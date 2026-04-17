#!/bin/bash
# Run on Proxmox VE node as root. Ensures listed guests start when the hypervisor boots.
#
# Usage:
#   ./pve-set-onboot-production.sh 101 102 103 104 105
# Or:
#   CRITICAL_VMIDS="101 102 103" ./pve-set-onboot-production.sh
#
# Map VMIDs from: qm list   (IPs 187/188/189/191 are INSIDE guests — not VMIDs)

set -euo pipefail

IDS=()
if [[ -n "${CRITICAL_VMIDS:-}" ]]; then
  read -ra IDS <<< "${CRITICAL_VMIDS}"
elif [[ $# -gt 0 ]]; then
  IDS=("$@")
else
  echo "Usage: $0 <vmid> [vmid ...]"
  echo "   or: CRITICAL_VMIDS='101 102' $0"
  exit 1
fi

echo "Setting onboot=1 for VMIDs: ${IDS[*]}"

for vmid in "${IDS[@]}"; do
  if ! qm status "$vmid" &>/dev/null; then
    echo "WARN: VM $vmid not found — skip"
    continue
  fi
  qm set "$vmid" --onboot 1
  echo "  VM $vmid: onboot=1"
done

echo "Done. After PVE reboot, these guests autostart unless manually stopped."
