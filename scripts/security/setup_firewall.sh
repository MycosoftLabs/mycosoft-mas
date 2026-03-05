#!/bin/bash
# setup_firewall.sh - VLAN-aware ufw rules for Mycosoft VMs
# Run with sudo. Restricts inbound to necessary ports from specific subnets.
#
# VLAN layout (from docs):
#   VLAN 10 (Internal): 10.10.10.0/24 - Backend services
#   VLAN 20 (DMZ):      10.10.20.0/24 - Web-facing
#   VLAN 30 (Mgmt):     10.10.30.0/24 - Monitoring, admin
#   VLAN 40 (IoT):      10.10.40.0/24 - MycoBrain devices
#
# For 192.168.0.x layout, use INTERNAL_CIDR=192.168.0.0/24
#
# Env:
#   INTERNAL_CIDR  - Internal subnet (default: 192.168.0.0/24)
#   DRY_RUN        - If set, print rules only, don't apply

set -e

INTERNAL_CIDR="${INTERNAL_CIDR:-192.168.0.0/24}"
DRY_RUN="${DRY_RUN:-}"

apply() {
  if [ -n "${DRY_RUN}" ]; then
    echo "[DRY RUN] $*"
  else
    "$@"
  fi
}

echo "Configuring firewall for ${INTERNAL_CIDR}..."

apply ufw default deny incoming
apply ufw default allow outgoing

# Allow SSH from internal only
apply ufw allow from "${INTERNAL_CIDR}" to any port 22 proto tcp comment 'SSH'

# MAS (8001), n8n (5678), Ollama (11434) - internal
apply ufw allow from "${INTERNAL_CIDR}" to any port 8001 proto tcp comment 'MAS Orchestrator'
apply ufw allow from "${INTERNAL_CIDR}" to any port 5678 proto tcp comment 'n8n'
apply ufw allow from "${INTERNAL_CIDR}" to any port 11434 proto tcp comment 'Ollama'

# MINDEX (8000), Postgres (5432), Redis (6379), Qdrant (6333) - internal
apply ufw allow from "${INTERNAL_CIDR}" to any port 8000 proto tcp comment 'MINDEX API'
apply ufw allow from "${INTERNAL_CIDR}" to any port 5432 proto tcp comment 'PostgreSQL'
apply ufw allow from "${INTERNAL_CIDR}" to any port 6379 proto tcp comment 'Redis'
apply ufw allow from "${INTERNAL_CIDR}" to any port 6333 proto tcp comment 'Qdrant'

# Website (3000) - allow internal; add DMZ/mgmt if needed
apply ufw allow from "${INTERNAL_CIDR}" to any port 3000 proto tcp comment 'Website'

# MycoBrain (8003) - internal + IoT
apply ufw allow from "${INTERNAL_CIDR}" to any port 8003 proto tcp comment 'MycoBrain'

# Prometheus (9090), Grafana (3002) - mgmt/internal
apply ufw allow from "${INTERNAL_CIDR}" to any port 9090 proto tcp comment 'Prometheus'
apply ufw allow from "${INTERNAL_CIDR}" to any port 3002 proto tcp comment 'Grafana'

# Allow established/related
apply ufw allow established

if [ -z "${DRY_RUN}" ]; then
  apply ufw --force enable
  apply ufw status verbose
else
  echo "DRY RUN complete. Run without DRY_RUN to apply."
fi
