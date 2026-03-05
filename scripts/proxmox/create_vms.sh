#!/bin/bash
# create_vms.sh - Creates Mycosoft service VMs by cloning from Ubuntu template
# Run on Proxmox host. Requires: create_template.sh to have been run first.
#
# Usage:
#   ./create_vms.sh [all|mindex|website|mas|mycobrain|monitoring]
#
# Environment (required for cloud-init user/password):
#   VM_CI_PASSWORD    - Cloud-init default user password (set via env, never commit)
#   VM_CI_USER        - Cloud-init user (default: mycosoft)
#
# Optional env:
#   TEMPLATE_ID       - Source template VM ID (default: 9000)
#   STORAGE           - Proxmox storage (default: local-lvm)
#   BRIDGE            - Network bridge (default: vmbr0)
#
# VM role to ID/CPU/RAM/disk mapping (overridable via env):
#   MINDEX:     ID=189  CPU=4  RAM=8192  DISK=100G  VLAN=10
#   WEBSITE:    ID=187  CPU=2  RAM=4096  DISK=50G   VLAN=20
#   MAS:        ID=188  CPU=4  RAM=8192  DISK=50G   VLAN=10
#   MYCOBRAIN:  ID=191  CPU=2  RAM=2048  DISK=20G   VLAN=40
#   MONITORING: ID=190  CPU=2  RAM=4096  DISK=100G  VLAN=30

set -e

TEMPLATE_ID="${TEMPLATE_ID:-9000}"
STORAGE="${STORAGE:-local-lvm}"
BRIDGE="${BRIDGE:-vmbr0}"
CI_USER="${VM_CI_USER:-mycosoft}"

if [ -z "${VM_CI_PASSWORD}" ]; then
  echo "ERROR: VM_CI_PASSWORD must be set (cloud-init password). Export it before running."
  exit 1
fi

create_vm() {
  local role="$1"
  local vmid="$2"
  local cpu="$3"
  local mem="$4"
  local disk="$5"
  local vlan="$6"

  if qm status "${vmid}" 2>/dev/null; then
    echo "VM ${vmid} (${role}) already exists, skipping."
    return 0
  fi

  echo "Creating ${role} VM (ID ${vmid}, ${cpu}c/${mem}MB/${disk})..."
  qm clone "${TEMPLATE_ID}" "${vmid}" --name "mycosoft-${role}" --full

  qm set "${vmid}" --cores "${cpu}" --memory "${mem}"
  qm set "${vmid}" --ciuser "${CI_USER}" --cipassword "${VM_CI_PASSWORD}"
  qm set "${vmid}" --net0 "virtio,bridge=${BRIDGE},tag=${vlan}"

  if [ -n "${disk}" ] && [ "${disk}" != "0" ]; then
    qm resize "${vmid}" scsi0 "${disk}"
  fi

  echo "  ${role} VM ${vmid} created (not started). Run: qm start ${vmid}"
}

create_all() {
  # MINDEX (189): Database + API
  create_vm mindex 189 4 8192 100G 10

  # WEBSITE/Sandbox (187): Next.js, Docker
  create_vm website 187 2 4096 50G 20

  # MAS (188): Orchestrator, agents, n8n, Ollama
  create_vm mas 188 4 8192 50G 10

  # MYCOBRAIN (191): Device host, n8n, MYCA workspace
  create_vm mycobrain 191 2 2048 20G 40

  # MONITORING (190): Grafana, Prometheus (or GPU node - configurable)
  create_vm monitoring 190 2 4096 100G 30
}

case "${1:-all}" in
  mindex)    create_vm mindex 189 4 8192 100G 10 ;;
  website)   create_vm website 187 2 4096 50G 20 ;;
  mas)       create_vm mas 188 4 8192 50G 10 ;;
  mycobrain) create_vm mycobrain 191 2 2048 20G 40 ;;
  monitoring) create_vm monitoring 190 2 4096 100G 30 ;;
  all)       create_all ;;
  *)
    echo "Usage: $0 {all|mindex|website|mas|mycobrain|monitoring}"
    exit 1
    ;;
esac

echo "Done."
