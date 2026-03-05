#!/bin/bash
# create_template.sh - Creates Ubuntu 24.04 cloud-init base template for Mycosoft VMs
# Run on Proxmox host. Requires: wget, qm (Proxmox CLI)
#
# Usage:
#   ./create_template.sh [TEMPLATE_ID]
#
# Optional env:
#   TEMPLATE_ID    - Proxmox template VM ID (default: 9000)
#   STORAGE        - Proxmox storage (default: local-lvm)
#   BRIDGE         - Network bridge (default: vmbr0)
#
# After creation: qm template TEMPLATE_ID
# Then use create_vms.sh to clone service VMs.

set -e

TEMPLATE_ID="${TEMPLATE_ID:-9000}"
STORAGE="${STORAGE:-local-lvm}"
BRIDGE="${BRIDGE:-vmbr0}"
UBUNTU_IMAGE="noble-server-cloudimg-amd64.img"
IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/${UBUNTU_IMAGE}"

echo "Creating Ubuntu 24.04 template (ID ${TEMPLATE_ID})..."
echo "Storage: ${STORAGE}, Bridge: ${BRIDGE}"

# Download cloud image if not present
if [ ! -f "${UBUNTU_IMAGE}" ]; then
  echo "Downloading ${UBUNTU_IMAGE}..."
  wget -q --show-progress "${IMAGE_URL}"
fi

# Create VM
qm create "${TEMPLATE_ID}" --name "ubuntu-24.04-template" --memory 2048 --cores 2 \
  --net0 "virtio,bridge=${BRIDGE}" --ostype l26

# Import disk
qm importdisk "${TEMPLATE_ID}" "${UBUNTU_IMAGE}" "${STORAGE}"

# Attach disk
qm set "${TEMPLATE_ID}" --scsihw virtio-scsi-pci --scsi0 "${STORAGE}:vm-${TEMPLATE_ID}-disk-0"

# Set boot order
qm set "${TEMPLATE_ID}" --boot c --bootdisk scsi0

# Add cloud-init drive
qm set "${TEMPLATE_ID}" --ide2 "${STORAGE}:cloudinit"

# Enable QEMU guest agent (recommended for cloud-init)
qm set "${TEMPLATE_ID}" --agent enabled=1

# Convert to template (makes it non-startable, cloneable only)
qm template "${TEMPLATE_ID}"

echo "Template ${TEMPLATE_ID} created. Use create_vms.sh to clone service VMs."
