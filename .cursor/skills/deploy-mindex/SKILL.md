---
name: deploy-mindex
description: Deploy or restart the MINDEX API service on VM 192.168.0.189. Use when updating MINDEX, restarting the database API, or deploying MINDEX changes.
---

# Deploy MINDEX API Service

## CRITICAL: Execute Deployment Yourself

**NEVER ask the user to run these steps or set VM_PASSWORD.** You MUST execute the deployment yourself. Load credentials: `Get-Content ".credentials.local" | ForEach-Object { if ($_ -match "^([^#=]+)=(.*)$") { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process") } }` then run `python _deploy_mindex.py` from MINDEX/mindex. Credentials live in MAS repo `.credentials.local`. See rule `agent-must-execute-operations.mdc`.

## Prerequisites

- SSH access to MINDEX VM at 192.168.0.189
- MINDEX code path on VM: `/home/mycosoft/mindex` (NOT /home/mycosoft/mas)

## Deployment Steps

```
Deployment Progress:
- [ ] Step 1: SSH to MINDEX VM
- [ ] Step 2: Pull latest code
- [ ] Step 3: Stop MINDEX API
- [ ] Step 4: Rebuild and start
- [ ] Step 5: Health check
```

### Step 1: SSH to MINDEX VM

```bash
ssh mycosoft@192.168.0.189
```

### Step 2: Pull latest code

```bash
cd /home/mycosoft/mindex
git fetch origin
git reset --hard origin/main
```

### Step 3: Stop MINDEX API

```bash
docker compose stop mindex-api
docker compose rm -f mindex-api
```

### Step 4: Rebuild and start

```bash
docker compose build --no-cache mindex-api
docker compose up -d mindex-api
```

### Step 5: Health check

```bash
sleep 5
curl -s http://localhost:8000/health
curl -s http://192.168.0.189:8000/docs
```

## Key Details

| Item | Value |
|------|-------|
| VM IP | 192.168.0.189 |
| VM User | mycosoft |
| API Port | 8000 |
| Health | http://192.168.0.189:8000/health |
| Docs | http://192.168.0.189:8000/docs |

## Database Services on MINDEX VM

These run independently and should NOT be restarted during API deploys:
- PostgreSQL: port 5432
- Redis: port 6379
- Qdrant: port 6333

## Troubleshooting

- **API won't start**: Check `docker compose logs mindex-api`
- **Database connection error**: Verify PostgreSQL is running on 5432
- **Vector search fails**: Check Qdrant service on 6333
