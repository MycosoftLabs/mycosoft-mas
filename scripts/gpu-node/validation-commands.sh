#!/bin/bash
# =============================================================================
# GPU Node Validation Commands
# Quick verification after bootstrap - run these to confirm everything works
# =============================================================================

echo "=== 1. SYSTEM INFO ==="
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "Kernel: $(uname -r)"
echo "Ubuntu: $(lsb_release -d | cut -f2)"
echo ""

echo "=== 2. NVIDIA DRIVER ==="
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo "Driver Status: OK"
else
    echo "Driver Status: NOT INSTALLED"
fi
echo ""

echo "=== 3. DOCKER ==="
if systemctl is-active --quiet docker; then
    echo "Docker: Running"
    docker --version
else
    echo "Docker: NOT RUNNING"
fi
echo ""

echo "=== 4. DOCKER GPU ACCESS ==="
if docker info 2>/dev/null | grep -q "nvidia"; then
    echo "NVIDIA Runtime: Configured"
    echo "Testing GPU in container..."
    docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null && echo "Container GPU: OK" || echo "Container GPU: FAILED"
else
    echo "NVIDIA Runtime: NOT CONFIGURED"
fi
echo ""

echo "=== 5. SSH SERVICE ==="
if systemctl is-active --quiet sshd; then
    echo "SSH: Running on port $(grep -E "^Port" /etc/ssh/sshd_config 2>/dev/null || echo "22 (default)")"
else
    echo "SSH: NOT RUNNING"
fi
echo ""

echo "=== 6. FIREWALL ==="
if command -v ufw &> /dev/null && ufw status | grep -q "active"; then
    echo "UFW: Active"
    ufw status | grep -E "^(22|8998|8999|8220|8300)" | head -5
else
    echo "UFW: Inactive or not installed"
fi
echo ""

echo "=== 7. RESOURCES ==="
echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk /: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
echo "GPU Memory: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "N/A")"
echo ""

echo "=== 8. SUMMARY ==="
echo "Ready for GPU workloads: $(nvidia-smi &>/dev/null && docker info 2>/dev/null | grep -q nvidia && echo YES || echo NO)"
