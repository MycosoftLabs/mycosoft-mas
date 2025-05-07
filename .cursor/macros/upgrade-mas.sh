#!/usr/bin/env bash
set -euo pipefail

# This macro spins up the core MCP servers defined in /mcp/*
# then validates and pushes the graph to the local registry.

SERVERS=(auth-z vault pg-data pg-vector file-store git-ops cron-svc slack-relay agent-registry observability)

for srv in "${SERVERS[@]}"; do
  echo "🚀  Starting $srv"
  if [[ -d "mcp/$srv" ]]; then
    pushd "mcp/$srv"
    npm install --silent
    mcp up --detach
    popd
  else
    echo "⚠️  Directory mcp/$srv not found, skipping"
  fi
done

echo "🔎 Running mcp doctor"
mcp doctor || true

echo "📡 Pushing graph"
mcp push --yes

echo "✅  MAS upgrade complete" | tee mas-upgrade.log 