#!/usr/bin/env bash
set -euo pipefail

cd /opt/mycosoft/website
git fetch origin
git reset --hard origin/main

if [ ! -f .env.local ]; then
  touch .env.local
fi

if ! grep -q "^NEXTAUTH_SECRET=" .env.local; then
  SECRET="$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
  echo "NEXTAUTH_SECRET=${SECRET}" >> .env.local
fi

DOCKER_BUILDKIT=0 docker build -f Dockerfile.production -t website-website:latest --no-cache .
docker rm -f mycosoft-website >/dev/null 2>&1 || true
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped website-website:latest

