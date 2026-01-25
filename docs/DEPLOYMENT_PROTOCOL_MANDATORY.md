# MANDATORY DEPLOYMENT PROTOCOL
## Every Deployment MUST Follow These Steps

**Version**: 1.0  
**Created**: January 21, 2026  
**Classification**: CRITICAL - ALL AGENTS MUST READ BEFORE DEPLOYING

---

## ⚠️ PRE-DEPLOYMENT CHECKLIST

Before ANY deployment, verify:
- [ ] Local changes tested on localhost:3010
- [ ] All changes committed and pushed to GitHub main branch
- [ ] No active builds running on VM
- [ ] VM memory usage < 70% (check with `check_vm_memory.py`)

---

## DEPLOYMENT STEPS (Execute in Order)

### Step 1: CLEAN DOCKER ENVIRONMENT

```bash
# ON VM - Always run these FIRST
docker system prune -f                    # Remove unused containers/networks
docker builder prune -f                   # Clear build cache
docker image prune -f                     # Remove dangling images
```

**Why:** Prevents memory buildup from repeated builds. This is what caused the 61GB memory issue.

---

### Step 2: PULL LATEST CODE

```bash
# ON VM
cd /home/mycosoft/mycosoft/website
git fetch origin main
git reset --hard origin/main
```

**Why:** Ensures we're deploying the latest committed code.

---

### Step 3: BUILD WITH NO-CACHE

```bash
# ON VM - CRITICAL: Always use --no-cache
cd /home/mycosoft/mycosoft/mas
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache
```

**Why:** Cached layers may contain stale code. `--no-cache` ensures fresh build.

---

### Step 4: FORCE RECREATE CONTAINER

```bash
# ON VM
docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website
```

**Why:** `--force-recreate` ensures new image is used, not old container.

---

### Step 5: VERIFY CONTAINER RUNNING

```bash
# ON VM
docker ps | grep website
docker logs mycosoft-always-on-mycosoft-website-1 --tail 20
```

**Expected:** Container shows "Up" status, logs show no errors.

---

### Step 6: PURGE CLOUDFLARE CACHE

**Option A - Dashboard:**
1. Go to https://dash.cloudflare.com
2. Select mycosoft.com domain
3. Caching → Configuration → **Purge Everything**

**Option B - API (when credentials set):**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

**Why:** Cloudflare caches static assets. Without purge, users see old content.

---

### Step 7: VERIFY DEPLOYMENT

```bash
# Quick checks
curl -s https://sandbox.mycosoft.com/api/health
curl -s https://sandbox.mycosoft.com -o /dev/null -w "%{http_code}"
```

**Test URLs:**
- https://sandbox.mycosoft.com - Homepage loads
- https://sandbox.mycosoft.com/security - SOC Dashboard with tour button
- https://sandbox.mycosoft.com/natureos/devices - Device manager

---

## COMMON FAILURE MODES

### Memory Issue (61GB+ usage)
**Cause:** Repeated builds without cleanup
**Fix:** Run `docker system prune -a -f` (warning: removes all unused images)

### "No services to build"
**Cause:** Wrong directory or cached compose state
**Fix:** 
```bash
cd /home/mycosoft/mycosoft/mas
docker compose -f docker-compose.always-on.yml down
docker rmi $(docker images -q mycosoft-website)
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache
```

### Stale content after deployment
**Cause:** Cloudflare cache not purged
**Fix:** Purge cache via dashboard immediately

### "Port already allocated"
**Cause:** Old container still running
**Fix:**
```bash
docker stop mycosoft-always-on-mycosoft-website-1
docker rm mycosoft-always-on-mycosoft-website-1
docker compose -f docker-compose.always-on.yml up -d mycosoft-website
```

---

## ENVIRONMENT VARIABLES (Critical)

These MUST be set in `/home/mycosoft/mycosoft/mas/.env`:

```bash
# Supabase (CRITICAL - needed at BUILD time)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Auth
NEXTAUTH_URL=https://sandbox.mycosoft.com
NEXTAUTH_SECRET=<32-char-secret>
```

These MUST be passed as `build.args` in `docker-compose.always-on.yml` for NEXT_PUBLIC_* variables.

---

## BUILD CONTEXT STRUCTURE

The `docker-compose.always-on.yml` expects:
```
/home/mycosoft/mycosoft/
├── mas/                              # MAS repo (contains docker-compose.always-on.yml)
│   └── docker-compose.always-on.yml
└── website/                          # Website repo (or symlink to it)
    └── Dockerfile.container
```

Build context in compose file: `../../WEBSITE/website` → resolves to `/home/mycosoft/WEBSITE/website`

If this doesn't exist, create symlink:
```bash
mkdir -p /home/mycosoft/WEBSITE
ln -sf /home/mycosoft/mycosoft/website /home/mycosoft/WEBSITE/website
```

---

## INSTANT DEPLOY COMMAND SEQUENCE

For fast deployments after this protocol is understood:

```bash
# Run from MAS directory on Windows
python scripts/deploy_with_protocol.py
```

This script will:
1. Check VM status
2. Prune Docker
3. Pull code
4. Build with no-cache
5. Force recreate
6. Verify
7. Purge Cloudflare

---

## POST-DEPLOYMENT VERIFICATION CHECKLIST

- [ ] Homepage loads at sandbox.mycosoft.com
- [ ] Login redirects to home (/) not dashboard
- [ ] Security page shows tour button
- [ ] Compliance tab works
- [ ] No console errors in browser

---

*This protocol is MANDATORY for all deployments.*
*Failure to follow may result in stale deployments or memory issues.*
