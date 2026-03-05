#!/bin/bash
# Setup noVNC + x11vnc on VM 191 for watching MYCA work on the desktop.
# Run as mycosoft on VM 191.
# Date: 2026-03-05

set -e

echo "Installing noVNC, websockify, x11vnc..."
sudo apt-get update -qq
sudo apt-get install -y novnc websockify x11vnc xdotool scrot

echo "Creating systemd service for x11vnc..."
sudo tee /etc/systemd/system/x11vnc-myca.service > /dev/null << 'EOF'
[Unit]
Description=x11vnc for MYCA desktop (display :0)
After=display-manager.service

[Service]
Type=simple
User=mycosoft
ExecStart=/usr/bin/x11vnc -display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Creating systemd service for noVNC websockify..."
sudo tee /etc/systemd/system/novnc-myca.service > /dev/null << 'EOF'
[Unit]
Description=noVNC proxy for MYCA (port 6080)
After=x11vnc-myca.service

[Service]
Type=simple
User=mycosoft
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 6080 localhost:5900
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "Enable and start: sudo systemctl enable --now x11vnc-myca novnc-myca"
echo "Access noVNC at: http://192.168.0.191:6080"
