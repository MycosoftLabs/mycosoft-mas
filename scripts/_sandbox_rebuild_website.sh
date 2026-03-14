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

DOCKER_BUILDKIT=0 docker compose --env-file .env.local -f docker-compose.production.yml build --no-cache website
docker compose --env-file .env.local -f docker-compose.production.yml up -d website

docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "mycosoft-website|mycosoft-tunnel"

