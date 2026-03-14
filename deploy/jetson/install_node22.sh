#!/usr/bin/env bash
# Install Node.js 22 on Jetson (Ubuntu ARM64) via NodeSource.
# Run with: sudo bash install_node22.sh
# OpenClaw and other tools require Node 22+.

set -e

echo "=== Node.js 22 Install (ARM64) ==="

# NodeSource setup (Ubuntu; works on arm64)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

echo "Installed: $(node -v) $(npm -v)"
echo "=== Done ==="
