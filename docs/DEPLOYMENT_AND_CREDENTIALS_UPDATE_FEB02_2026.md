# Deployment & Credentials Update - February 2, 2026

## Summary

This document covers all work completed on February 2, 2026 including:
- PR merges from mobile development work
- Bug fixes for n8n webhook integration
- Sandbox deployment automation
- Cloudflare cache purge automation
- MAS repo permission fixes

---

## 1. PR Merges

### PR #71: PersonaPlex Multi-Agent Bridging
- **Branch:** `cursor/personaplex-multi-agent-bridging-f119`
- **Repository:** mycosoft-mas
- **Key Changes:**
  - Full-duplex voice with Moshi integration
  - Intent classification (action/query/confirm/cancel)
  - Confirmation gating for destructive commands
  - Rate limiting and deduplication
  - Real n8n webhook calls (replaced mock responses)

### PR #3: Earth-2 Platform Integration
- **Branch:** `cursor/earth-2-platform-integration-a9ce`
- **Repository:** NatureOS
- **Key Changes:**
  - NVIDIA Earth-2 integration strategy
  - CREP and FUSARIUM system connections
  - NatureOS master integration plan

---

## 2. Bug Fixes

### N8N Webhook URL Duplication Fix
**Problem:** MAS orchestrator was calling `/webhook/webhook/myca/command` (duplicated path)

**Files Modified:**
- `mycosoft_mas/core/myca_main.py`
- `mycosoft_mas/core/orchestrator_service.py`

**Fix:** Updated `resolve_n8n_webhook_url()` to not modify the base URL:
```python
def resolve_n8n_webhook_url() -> str | None:
    base = os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_URL")
    if not base:
        return None
    base = base.rstrip("/")
    # Don't modify base - n8n client handles webhook path
    return base
```

### Docker Compose Syntax Error
**Problem:** `docker-compose.yml` had syntax error: `- mas-networkvolumes:` on one line

**Fix:** Separated network and volumes sections properly

---

## 3. Sandbox Deployment Automation

### New Script: `scripts/deploy_sandbox_full.py`

Complete deployment automation that:
1. SSH to sandbox VM (192.168.0.187)
2. Pull latest MAS repository code
3. Pull latest Website repository code
4. Rebuild website Docker image
5. Stop and remove old container
6. Start new container with fresh image
7. Verify container health
8. Purge Cloudflare cache automatically

**Usage:**
```bash
python scripts/deploy_sandbox_full.py
```

### Helper Scripts Created
| Script | Purpose |
|--------|---------|
| `_deploy_sandbox.py` | Initial deployment attempts |
| `_check_sandbox.py` | Check sandbox container status |
| `_restart_sandbox.py` | Restart container only |
| `_start_website.py` | Start website container directly |

---

## 4. MAS Repo Permissions Fix

**Problem:** Git operations failing with "Permission denied" on `/home/mycosoft/mycosoft/mas/.git/FETCH_HEAD`

**Fix:** Via SSH with sudo:
```bash
sudo chown -R mycosoft:mycosoft /home/mycosoft/mycosoft/mas/.git
```

**Result:** Git fetch now works correctly on sandbox

---

## 5. Cloudflare Cache Purge Automation

### Previous Issue
- Old Zone ID: `afd4d5ce84fb58d7a6e2fb98a207fbc6` (incorrect)
- Old API Token: `4YL2fJMqQBJiJQSVZqVVi-MF_cHTbnA1FVvEH8Dh` (expired)

### Updated Configuration
| Setting | Value |
|---------|-------|
| Zone ID | `af274016182495aeac049ac2c1f07b6d` |
| API Token | `BdvbQeLwi_yxOBUpJJIGF8eWmGKX-HQFKzn_aLkb` |

### Files Updated
- `scripts/deploy_sandbox_full.py` - New deploy script with correct credentials
- `scripts/direct_deploy_and_purge.py` - Updated zone ID and token
- `.env.example` - Added Cloudflare and n8n configuration

---

## 6. All Credentials Reference

### Sandbox VM SSH
| Setting | Value |
|---------|-------|
| Host | `192.168.0.187` |
| Username | `mycosoft` |
| Password | `Mushroom1!Mushroom1!` |

### n8n Workflow Automation
| Setting | Value |
|---------|-------|
| URL | `http://localhost:5678` |
| Webhook URL | `http://localhost:5678/webhook` |
| Username | `morgan@mycosoft.org` |
| Password | `Mushroom1!Mushroom1!` |

### Cloudflare
| Setting | Value |
|---------|-------|
| Zone | `mycosoft.com` |
| Zone ID | `af274016182495aeac049ac2c1f07b6d` |
| API Token | `BdvbQeLwi_yxOBUpJJIGF8eWmGKX-HQFKzn_aLkb` |

---

## 7. Sandbox VM Structure

### Repository Locations
| Repo | Path |
|------|------|
| MAS | `/home/mycosoft/mycosoft/mas` |
| Website | `/opt/mycosoft/website` |
| Docker Compose | `/opt/mycosoft/docker-compose.yml` |

### Running Containers
| Container | Status | Image |
|-----------|--------|-------|
| mycosoft-website | healthy | website-website:latest |
| mycosoft-postgres | healthy | postgres |
| mycosoft-redis | healthy | redis |
| mycorrhizae-api | healthy | - |
| mycorrhizae-redis | running | redis |
| mindex-api | running | - |
| mindex-etl-scheduler | running | - |

---

## 8. Git Commits Today

```
bca72c9 - fix: Update Cloudflare zone ID and API token (Feb 2, 2026)
6f42d1d - feat: Add full sandbox deploy script with Cloudflare purge (Feb 2, 2026)
95fe428 - docs: Complete sandbox deployment report (Feb 2, 2026)
ef2f8ff - fix: N8N webhook URL construction and docker-compose syntax (Feb 2, 2026)
116df07 - docs: Add Earth-2 and NatureOS integration plans from PR #3
```

---

## 9. Deployment Workflow

### Standard Deploy Process
```bash
# 1. Make code changes locally
# 2. Test on localhost
npm run dev  # or python -m uvicorn...

# 3. Commit and push
git add .
git commit -m "your message"
git push origin main

# 4. Deploy to sandbox (automated)
python scripts/deploy_sandbox_full.py

# This will:
# - SSH to VM
# - Pull latest code
# - Rebuild Docker image
# - Restart container
# - Purge Cloudflare cache

# 5. Verify
# https://sandbox.mycosoft.com
```

---

## 10. Remaining Action Items

### n8n Workflow Activation
The `myca/command` workflow needs to be manually activated:
1. Open http://localhost:5678
2. Login with `morgan@mycosoft.org` / `Mushroom1!Mushroom1!`
3. Import workflow from `n8n/workflows/01_myca_command_api.json`
4. Activate the workflow

### Website Health Status
Current health check shows:
- ✅ API: operational
- ⚠️ Database: NEON_DATABASE_URL not configured (expected for sandbox)
- ⚠️ MAS API: Not deployed on sandbox VM

---

## 11. Testing Completed

| Test | Result |
|------|--------|
| PersonaPlex full-duplex audio | ✅ Working |
| Intent classification | ✅ Working |
| Confirmation gating | ✅ Working |
| MINDEX voice API | ✅ Working |
| Voice commands parsing | ✅ Working |
| Unifi Dashboard UI | ✅ Working |
| Sandbox deployment | ✅ Working |
| Cloudflare cache purge | ✅ Working |

---

*Document created: February 2, 2026*
*Author: Cursor AI Assistant*
