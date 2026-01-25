# Deployment Session - January 21, 2026

## Summary
Successfully deployed Mushroom 1 page redesign to sandbox.mycosoft.com after troubleshooting multiple deployment issues.

## Changes Deployed

### Hero Section
- Badge: "Environmental drone" (was "Pre-Order Now - $2,000")
- Title: "Mushroom 1"
- Subtitle: "The world's first real droid." (was "The world's first ground-based fungal intelligence station")
- Tagline: "Giving nature its own computer." (was "Giving nature a voice")

### Pre-Order Modal
- Full-width video (close 1.mp4)
- Device overview, included items, features
- Deployment timeline (mid-to-end 2026)

### Inside Mushroom 1 Section
- Redesigned with "control device" aesthetic
- Component Selector panel with 10 selectable components
- Interactive Blueprint on the right
- Component Details panel below selector
- All components have icons and detailed descriptions

### Section Order
- Advanced Sensor Suite moved above "In the Wild" gallery

## Issues Encountered & Fixes

### Issue 1: Docker Compose Not Starting Container
- **Symptom**: `docker compose up -d mycosoft-website` returned but no container created
- **Cause**: Unknown compose issue with networking
- **Fix**: Used direct `docker run` command instead:
  ```bash
  docker run -d --name website-test \
    -p 3000:3000 \
    --restart unless-stopped \
    mycosoft-always-on-mycosoft-website:latest
  ```

### Issue 2: Symlinks in Website Directory
- **Symptom**: Build error "Cannot find /app/website"
- **Cause**: Previous symlink `/home/mycosoft/mycosoft/website/website` was getting copied into container
- **Fix**: Remove all symlinks in website directory before build:
  ```bash
  find /home/mycosoft/mycosoft/website -maxdepth 1 -type l -delete
  ```

### Issue 3: Stale Docker Cache
- **Symptom**: Old code being deployed despite git pull
- **Cause**: Docker build cache, image cache, Next.js cache
- **Fix**: Clean ALL caches before every deployment:
  ```bash
  docker system prune -af
  docker builder prune -af
  docker image prune -af
  rm -rf /home/mycosoft/mycosoft/website/.next
  ```

### Issue 4: Cloudflare Serving Stale Content
- **Symptom**: Website shows old content in browser
- **Cause**: Cloudflare CDN cache
- **Fix**: ALWAYS purge Cloudflare cache after deployment:
  - dash.cloudflare.com → mycosoft.com → Caching → Purge Everything

## Critical Paths to Remember

| Path | Purpose |
|------|---------|
| `/home/mycosoft/mycosoft/website` | Website source code |
| `/home/mycosoft/mycosoft/mas` | MAS repository with docker-compose |
| `/home/mycosoft/WEBSITE/website` | Symlink required for Docker build context |
| `/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml` | Production compose file |
| `/opt/mycosoft/media/website/assets` | NAS-mounted media files |

## Master Deployment Script

Created `scripts/MASTER_DEPLOY.py` - use this for all future deployments:

```bash
python scripts/MASTER_DEPLOY.py        # Full deployment with all cache clearing
python scripts/MASTER_DEPLOY.py --quick  # Skip cache clearing (dangerous)
python scripts/MASTER_DEPLOY.py --verify # Just verify current status
```

## Lessons Learned

1. **Never trust docker compose** - if container doesn't start, use direct `docker run`
2. **Always clear ALL caches** - Docker build cache, image cache, Next.js cache
3. **Check for rogue symlinks** - they get copied into containers and break builds
4. **Cloudflare purge is MANDATORY** - stale JS causes ChunkLoadError
5. **Use the MASTER_DEPLOY.py script** - it does everything correctly

## Verification

- ✅ sandbox.mycosoft.com/devices/mushroom-1 returns HTTP 200
- ✅ Hero section shows new text
- ✅ Pre-Order modal opens with video
- ✅ Component Selector has all 10 components
- ✅ Interactive Blueprint is functional

---
*Session completed at 8:45 PM EST*
*Commit: b06c1ac (Mushroom 1 page redesign)*
