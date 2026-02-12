---
name: deploy-website-sandbox
description: Deploy the Mycosoft website to the Sandbox VM (192.168.0.187). Use when the user asks to deploy, push to sandbox, rebuild the website container, or update the live site.
---

# Deploy Website to Sandbox VM

## CRITICAL: Execute Deployment Yourself

**NEVER ask the user to run these steps.** You MUST execute the deployment yourself via run_terminal_cmd (SSH, or deploy scripts like `_rebuild_sandbox.py`). Load credentials from `.credentials.local` before SSH. See rule `agent-must-execute-operations.mdc`.

## Prerequisites

- Code committed and pushed to GitHub (main branch)
- SSH access to Sandbox VM at 192.168.0.187

## Deployment Steps

Copy this checklist and track progress:

```
Deployment Progress:
- [ ] Step 1: SSH to Sandbox VM
- [ ] Step 2: Pull latest code
- [ ] Step 3: Stop and remove old container
- [ ] Step 4: Rebuild Docker image
- [ ] Step 5: Start new container with NAS mount
- [ ] Step 6: Health check
- [ ] Step 7: Purge Cloudflare cache
- [ ] Step 8: Verify deployment
```

### Step 1: SSH to Sandbox VM

```bash
ssh mycosoft@192.168.0.187
```

### Step 2: Pull latest code

```bash
cd /opt/mycosoft/website
git fetch origin
git reset --hard origin/main
```

### Step 3: Stop and remove old container

```bash
docker stop mycosoft-website
docker rm mycosoft-website
```

### Step 4: Rebuild Docker image (no cache)

```bash
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .
```

### Step 5: Start new container with NAS volume mount

**CRITICAL**: Always include the NAS volume mount for media assets.

```bash
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

### Step 6: Health check

```bash
# Wait for container to start
sleep 10
# Check container is running
docker ps | grep mycosoft-website
# Test HTTP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: Container running, HTTP 200.

### Step 7: Purge Cloudflare cache

Go to Cloudflare Dashboard > mycosoft.com > Caching > Purge Everything.
Or use the Cloudflare API:

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

### Step 8: Verify deployment

Compare localhost:3010 (dev) vs sandbox.mycosoft.com (production) to confirm changes are live.

## Key Details

| Item | Value |
|------|-------|
| VM IP | 192.168.0.187 |
| VM User | mycosoft |
| Code Path | /opt/mycosoft/website |
| Container | mycosoft-website |
| Image | mycosoft-always-on-mycosoft-website:latest |
| Port | 3000 |
| NAS Mount | /opt/mycosoft/media/website/assets:/app/public/assets:ro |

## Troubleshooting

- **Build fails**: Check Dockerfile, ensure Node 18 compatibility
- **Container won't start**: Check `docker logs mycosoft-website`
- **Videos not loading**: Verify NAS mount is included in docker run command
- **Changes not visible**: Ensure Cloudflare cache was purged
