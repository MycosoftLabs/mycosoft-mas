#!/bin/bash
# ================================================================
# MYCA VM 191 — Quick Start
# Run this from Sandbox VM (192.168.0.187) or any LAN machine
# ================================================================
set -euo pipefail

echo "============================================"
echo "  MYCA VM 191 — Quick Provisioning"
echo "============================================"
echo ""

# Check we're on the LAN
if ! ping -c 1 -W 2 192.168.0.202 &>/dev/null; then
    echo "ERROR: Cannot reach Proxmox (192.168.0.202)."
    echo "Run this from a machine on the 192.168.0.x network."
    exit 1
fi

# Check for Python3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Install deps
echo "Installing Python dependencies..."
pip3 install --quiet requests paramiko 2>/dev/null || pip install --quiet requests paramiko

# Navigate to script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check for credentials
if [ ! -f "../../.credentials.local" ] && [ -z "${PROXMOX_TOKEN_ID:-}" ]; then
    echo ""
    echo "No credentials found. Set these environment variables:"
    echo ""
    echo "  # Option A: Proxmox API token"
    echo "  export PROXMOX_TOKEN_ID='root@pam!myca'"
    echo "  export PROXMOX_TOKEN_SECRET='your-token-secret'"
    echo ""
    echo "  # Option B: Proxmox root password"
    echo "  export PROXMOX_PASSWORD='your-password'"
    echo ""
    echo "  # Required: password for the new VM"
    echo "  export VM_PASSWORD='your-vm-password'"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo ""
echo "Starting provisioning..."
echo ""

# Run the provisioning script
python3 provision_myca_vm_191.py "$@"

echo ""
echo "============================================"
echo "  Next Steps:"
echo "  1. Fill in /opt/myca/.env on the VM with real API tokens"
echo "  2. Set up Slack bot: https://api.slack.com/apps"
echo "  3. Set up Discord bot: https://discord.com/developers"
echo "  4. Add Google service account JSON to /opt/myca/credentials/google/"
echo "  5. Register with MAS orchestrator:"
echo "     curl -X POST http://192.168.0.188:8001/api/registry/agents \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"agent_id\":\"workspace_agent\",\"name\":\"MYCA Workspace\",\"vm\":\"192.168.0.191\"}'"
echo "============================================"
