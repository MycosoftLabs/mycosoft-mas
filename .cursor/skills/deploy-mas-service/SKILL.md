---
name: deploy-mas-service
description: Deploy or restart the MAS orchestrator service on VM 192.168.0.188. Use when updating the Multi-Agent System, restarting the orchestrator, or deploying MAS changes.
---

# Deploy MAS Orchestrator Service

## Prerequisites

- Code committed and pushed to GitHub
- SSH access to MAS VM at 192.168.0.188

## Deployment Steps

```
Deployment Progress:
- [ ] Step 1: SSH to MAS VM
- [ ] Step 2: Pull latest code
- [ ] Step 3: Rebuild Docker image
- [ ] Step 4: Restart container/service
- [ ] Step 5: Health check
```

### Step 1: SSH to MAS VM

```bash
ssh mycosoft@192.168.0.188
```

### Step 2: Pull latest code

```bash
cd /home/mycosoft/mycosoft/mas
git fetch origin
git reset --hard origin/main
```

### Step 3: Rebuild Docker image

```bash
docker build -t mycosoft/mas-agent:latest --no-cache .
```

### Step 4: Restart container

```bash
# Stop old container
docker stop myca-orchestrator-new
docker rm myca-orchestrator-new

# Start new container
docker run -d --name myca-orchestrator-new \
  --restart unless-stopped \
  -p 8001:8000 \
  -e REDIS_URL=redis://192.168.0.188:6379/0 \
  -e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex \
  -e N8N_URL=http://192.168.0.188:5678 \
  mycosoft/mas-agent:latest
```

Alternative (if using systemd service):

```bash
sudo systemctl restart mas-orchestrator
```

### Step 5: Health check

```bash
sleep 10
curl -s http://localhost:8001/health
curl -s http://192.168.0.188:8001/health
```

Expected: JSON response with status "healthy".

## Key Details

| Item | Value |
|------|-------|
| VM IP | 192.168.0.188 |
| VM User | mycosoft |
| Code Path | /home/mycosoft/mycosoft/mas |
| Container | myca-orchestrator-new |
| Image | mycosoft/mas-agent:latest |
| Port | 8001 (maps to 8000 internal) |
| Health | http://192.168.0.188:8001/health |

## Troubleshooting

- **Container won't start**: Check `docker logs myca-orchestrator-new`
- **Health check fails**: Verify port 8001 is not in use, check env vars
- **Import errors**: Ensure all Python dependencies are in pyproject.toml
