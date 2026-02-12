# Docker Management System (Feb 12, 2026)

Comprehensive Docker Desktop management integrated with Cursor and MAS for resource efficiency, container lifecycle, and local-to-VM coordination.

## Overview

This system ensures:
- Docker Desktop runs efficiently without wasting resources
- Only required containers run locally (n8n)
- Unused containers, images, and volumes are cleaned up automatically
- Docker health is reported to MAS for infrastructure monitoring
- Local testing coordinates properly with VM production

## Components

### 1. Cursor Rule (Always-Apply)
**File:** `.cursor/rules/docker-management.mdc`

Defines:
- Required local containers (only `mycosoft-n8n`)
- VM container reference
- Cleanup rules and resource limits
- MAS integration patterns
- Agent protocol for Docker management

### 2. Docker-Ops Sub-Agent
**File:** `.cursor/agents/docker-ops.md`

Specialized agent for:
- Docker troubleshooting
- Container lifecycle management
- Image cleanup and optimization
- MAS infrastructure reporting
- Local-to-VM coordination

### 3. Docker Healthcheck Script
**File:** `scripts/docker-healthcheck.ps1`

Usage:
```powershell
.\scripts\docker-healthcheck.ps1              # Quick health check
.\scripts\docker-healthcheck.ps1 -Quick       # Same as above
.\scripts\docker-healthcheck.ps1 -Cleanup     # Full cleanup
.\scripts\docker-healthcheck.ps1 -StartDocker # Start Docker Desktop
.\scripts\docker-healthcheck.ps1 -Json        # Output as JSON
.\scripts\docker-healthcheck.ps1 -ReportToMAS # Send to MAS API
```

### 4. Autostart Integration
**File:** `.cursor/rules/autostart-services.mdc`

Docker healthcheck is registered as service #6 for periodic monitoring.

## Required Local Containers

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `mycosoft-n8n` | `n8nio/n8n` | 5678 | Workflow automation |

**All database and API services run on VMs, not locally.**

## VM Containers Reference

| VM | Container | Port |
|----|-----------|------|
| 187 | `mycosoft-website` | 3000 |
| 187 | `mycorrhizae-api` | 8002 |
| 188 | `n8n` | 5678 |
| 188 | `ollama` | 11434 |
| 189 | `mindex-postgres` | 5432 |
| 189 | `mindex-redis` | 6379 |
| 189 | `mindex-qdrant` | 6333 |
| 189 | `mindex-api` | 8000 |

## Resource Limits

| Resource | Limit | Action if Exceeded |
|----------|-------|---------------------|
| Docker Desktop memory | 4GB | Reduce in settings |
| vmmem (WSL2) | 4GB | `wsl --shutdown` |
| Total images | 20 | Prune old images |
| Total containers | 10 | Remove stopped |
| Build cache | 5GB | `docker builder prune` |

## MAS Integration

### Reporting Docker Health

```powershell
# Generate and send health report to MAS
.\scripts\docker-healthcheck.ps1 -ReportToMAS
```

The report includes:
- Docker running status
- Container list with status
- Disk usage
- vmmem memory usage
- Issues detected

### MAS API Endpoint

```
POST http://192.168.0.188:8001/api/infrastructure/docker-health
```

## Cleanup Schedule

### Automatic (via autostart-healthcheck)
- Every 30 minutes during active sessions
- Reports anomalies to user

### Manual
```powershell
# Basic cleanup
.\scripts\docker-healthcheck.ps1 -Cleanup

# Full aggressive cleanup
docker system prune -a --volumes -f
docker builder prune -a -f
```

### Weekly Maintenance
```powershell
docker system prune -a --volumes -f
docker builder prune -a -f
```

## Quick Reference

```powershell
# Check Docker status
.\scripts\docker-healthcheck.ps1

# Full cleanup
.\scripts\docker-healthcheck.ps1 -Cleanup

# Start Docker + required containers
.\scripts\start-dev-environment.ps1

# Stop all Docker (free resources)
docker stop $(docker ps -q)
wsl --shutdown

# Check vmmem memory
Get-Process vmmem -ErrorAction SilentlyContinue | Select Name, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB)}}
```

## Related Documentation

- [ALWAYS_ON_SERVICES_FEB12_2026.md](ALWAYS_ON_SERVICES_FEB12_2026.md) - Full environment reference
- [TERMINAL_AND_PYTHON_OPERATIONS_GUIDE_FEB12_2026.md](TERMINAL_AND_PYTHON_OPERATIONS_GUIDE_FEB12_2026.md) - Process management
- `.cursor/rules/docker-management.mdc` - Docker rule
- `.cursor/agents/docker-ops.md` - Docker agent
- `scripts/docker-healthcheck.ps1` - Healthcheck script
