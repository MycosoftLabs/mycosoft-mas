---
name: vm-health-check
description: Check health of all Mycosoft VMs (Sandbox, MAS, MINDEX). Use when verifying system status, debugging connectivity, or after deployments.
---

# VM Health Check

Run health checks across all three Mycosoft VMs to verify services are running.

## VM Layout

| VM | IP | Role | Health Endpoint |
|----|-----|------|-----------------|
| Sandbox | 192.168.0.187 | Website | http://192.168.0.187:3000 |
| MAS | 192.168.0.188 | Orchestrator | http://192.168.0.188:8001/health |
| MINDEX | 192.168.0.189 | Database | http://192.168.0.189:8000/health |

## Quick Health Check

Run these curl commands to check all services:

```bash
# Sandbox VM - Website
curl -s -o /dev/null -w "Sandbox Website: %{http_code}\n" http://192.168.0.187:3000

# MAS VM - Orchestrator
curl -s http://192.168.0.188:8001/health

# MINDEX VM - Database API
curl -s http://192.168.0.189:8000/health
```

## Deep Health Check

### Sandbox VM (192.168.0.187)

```bash
ssh mycosoft@192.168.0.187 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

Key containers: `mycosoft-website` (port 3000)

### MAS VM (192.168.0.188)

```bash
ssh mycosoft@192.168.0.188 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

Key containers: `myca-orchestrator-new` (port 8001)
Additional services: Redis (6379), PostgreSQL (5432), n8n (5678)

### MINDEX VM (192.168.0.189)

```bash
ssh mycosoft@192.168.0.189 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

Key services: PostgreSQL (5432), Redis (6379), Qdrant (6333), MINDEX API (8000)

## Expected Results

- All health endpoints return 200 or JSON with status "healthy"
- All Docker containers show "Up" status
- No containers in "Restarting" or "Exited" state

## If a Service is Down

1. Check container logs: `docker logs <container_name> --tail 50`
2. Restart container: `docker restart <container_name>`
3. If persistent failure, rebuild using the deploy skill for that VM
