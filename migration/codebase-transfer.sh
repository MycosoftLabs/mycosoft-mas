#!/bin/bash
# Codebase Transfer Script
# Run this on Windows machine to transfer codebase to VM1

set -e

# Configuration
VM1_IP="${1:-192.168.1.100}"
VM1_USER="${2:-mycosoft}"
REMOTE_DIR="/opt/mycosoft"

echo "=========================================="
echo "Codebase Transfer to VM1"
echo "=========================================="
echo "Target: $VM1_USER@$VM1_IP:$REMOTE_DIR"
echo ""

# Check if rsync is available (preferred method)
if command -v rsync &> /dev/null; then
    echo "Using rsync for transfer..."
    
    # Transfer MAS codebase
    echo "[1/2] Transferring MAS codebase..."
    rsync -avz --progress \
        --exclude 'node_modules' \
        --exclude '.next' \
        --exclude 'venv*' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.git' \
        --exclude '*.log' \
        C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\ \
        $VM1_USER@$VM1_IP:$REMOTE_DIR/
    
    # Transfer website codebase (if separate)
    if [ -d "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website" ]; then
        echo "[2/2] Transferring website codebase..."
        rsync -avz --progress \
            --exclude 'node_modules' \
            --exclude '.next' \
            --exclude '.git' \
            C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\ \
            $VM1_USER@$VM1_IP:$REMOTE_DIR/website/
    fi
    
else
    echo "Using SCP for transfer (rsync not available)..."
    echo "NOTE: This may be slower. Consider installing rsync via WSL."
    
    # Transfer MAS codebase
    echo "[1/2] Transferring MAS codebase..."
    scp -r \
        C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\* \
        $VM1_USER@$VM1_IP:$REMOTE_DIR/
    
    # Transfer website codebase
    if [ -d "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website" ]; then
        echo "[2/2] Transferring website codebase..."
        scp -r \
            C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\* \
            $VM1_USER@$VM1_IP:$REMOTE_DIR/website/
    fi
fi

echo ""
echo "=========================================="
echo "Codebase transfer completed!"
echo "=========================================="
echo ""
echo "Next steps on VM1:"
echo "  1. SSH to VM1: ssh $VM1_USER@$VM1_IP"
echo "  2. Verify files: ls -la $REMOTE_DIR"
echo "  3. Run: cd $REMOTE_DIR && ./migration/setup-production.sh"
