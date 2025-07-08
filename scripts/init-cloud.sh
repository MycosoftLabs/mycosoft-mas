#!/bin/bash
# Basic VM initialization for cloud deployment
set -euo pipefail

sudo apt-get update && sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker

# Pull latest MAS image and start via docker-compose
cd /opt/mas || exit 1
sudo docker-compose pull
sudo docker-compose up -d
