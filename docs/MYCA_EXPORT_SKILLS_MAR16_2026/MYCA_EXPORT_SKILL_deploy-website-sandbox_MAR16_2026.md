# MYCA Export — Skill: Deploy Website Sandbox

**Export Date:** MAR16_2026  
**Skill Name:** deploy-website-sandbox  
**Purpose:** Deploy the Mycosoft website to the Sandbox VM (192.168.0.187). Use when the user asks to deploy, push to sandbox, rebuild the website container, or update the live site.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user requests website deployment.

---

## CRITICAL: Execute Deployment Yourself — Never Hand Off to User

**NEVER ask the user to deploy, SSH, run scripts, or debug.** Execute the deployment yourself. If it fails, fix the failure and retry until it succeeds. Load credentials from `.credentials.local` before SSH.

## Prerequisites

- Code committed and pushed to GitHub (main branch)
- SSH access to Sandbox VM at 192.168.0.187

## Deployment Steps

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
sleep 10
docker ps | grep mycosoft-website
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: Container running, HTTP 200.

### Step 7: Purge Cloudflare cache

Use deploy scripts that call `purge_everything()` after a successful deploy. Or from website repo: `python -c "from _cloudflare_cache import purge_everything; purge_everything()"`

### Step 8: Verify deployment

Compare localhost:3010 (dev) vs sandbox.mycosoft.com (production).

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

## NEVER Run or Recreate

- **`_sync_nas_push_from_windows.py`** — Deleted. It corrupted NAS and local videos.

## Troubleshooting (You Fix, Not User)

- **Build fails**: Fix Dockerfile, pnpm-lock.yaml, or package resolution; retry deploy
- **Container won't start**: Check `docker logs`, fix config, retry
- **Videos not loading**: Verify NAS mount in docker run command
- **Changes not visible**: Run purge (`purge_everything()` in _cloudflare_cache)
