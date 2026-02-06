# VM Memory Management Strategy - Feb 6, 2026

## Problem Identified
The Sandbox VM (192.168.0.187) is running at 89% memory utilization (56GB/62GB) with heavy swap usage (4.7GB/8GB), causing Docker operations to be extremely slow.

## Root Cause
- Old Docker images, containers, and build cache accumulating over deployments
- No memory limits on containers allowing unbounded growth
- Multiple services competing for limited memory

## Solutions Implemented

### 1. Docker Cache Cleanup on Every Deploy
Updated `scripts/fix_and_deploy.py` to ALWAYS clear Docker cache before deploying:
```python
# Step 0: ALWAYS Clear Docker Cache First (prevents memory bloat)
run_command(client, "docker container prune -f")
run_command(client, "docker image prune -a -f")
run_command(client, "docker volume prune -f")
run_command(client, "docker builder prune -a -f")
run_command(client, "docker system prune -f")
```

### 2. Memory Limits in docker-compose.always-on.yml
Added resource limits to website service:
```yaml
deploy:
  resources:
    limits:
      memory: 32G
    reservations:
      memory: 8G
```

### 3. Memory Allocation Strategy for 62GB VM

| Service | Max Memory | Notes |
|---------|------------|-------|
| Website Frontend | 32GB | Primary user-facing service |
| MINDEX API | 16GB | Database/search operations |
| MAS Orchestrator | 8GB | Agent coordination |
| System/Other | 6GB | OS, Docker daemon, etc. |

## Manual Cleanup Commands
If the VM becomes overloaded, run these commands via SSH:

```bash
# SSH into VM
ssh mycosoft@192.168.0.187
# Password: Mushroom1!Mushroom1!

# Stop all non-essential containers
docker stop $(docker ps -q --filter "name!=website" --filter "name!=mindex")

# Full Docker cleanup
docker system prune -a -f --volumes

# Check memory
free -h

# Restart Docker daemon
sudo systemctl restart docker

# Restart essential services
cd /home/mycosoft/mycosoft/mas
docker compose -f docker-compose.always-on.yml up -d mycosoft-website mindex-api
```

## Secondary Server Option
The rack has additional servers that can be used to offload services:
- Move MINDEX to separate server
- Move MAS orchestrator to separate server
- Keep website frontend on primary sandbox VM

## MycoBrain Service
The MycoBrain service runs on Windows PC (192.168.0.172:8765), not on the VM.
Environment variable set: `MYCOBRAIN_SERVICE_URL: http://192.168.0.172:8765`

## Deployment Process Reminder
Every deployment MUST:
1. Clear Docker cache first
2. Pull latest code
3. Rebuild containers (not just restart)
4. Clear Cloudflare cache if needed
