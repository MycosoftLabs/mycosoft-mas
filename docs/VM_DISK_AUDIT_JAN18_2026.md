# VM Disk Space Audit Report
**Date:** January 18, 2026  
**VM:** VM103 (192.168.0.187) - Mycosoft Production  
**Auditor:** AI Agent

---

## Executive Summary

### The Problem
The VM "ran out of space" during a Docker build, causing deployment failure.

### Root Cause
1. **Docker Build Cache** accumulated **10.34GB** from repeated builds
2. **LVM only allocated 98GB** of the 256GB+ virtual disk
3. **AI services consume 22GB** of Docker image space

### Immediate Fix Applied
- Cleared Docker build cache: **Freed 10GB**
- Space now: **43GB used / 51GB free (47%)**

---

## Disk Allocation Discrepancy

| Layer | Size | Notes |
|-------|------|-------|
| Proxmox shows | 274.88GB | VM103 disk-1 |
| VM boot disk | 256GB | What we allocated |
| **Ubuntu LVM** | **98GB** | What the OS can actually use! |
| Unallocated | ~158GB | Sitting unused |

**Action Required:** Expand LVM to use full disk capacity.

---

## Space Breakdown (Before Cleanup)

### By Directory (Total 74GB used)

| Path | Size | Contents |
|------|------|----------|
| `/var/lib/containerd` | 39GB | Container runtime snapshots |
| `/var/lib/docker` | 22GB | Docker images, containers, volumes |
| `/opt/mycosoft` | 1.6GB | Application code |
| `/usr` | 2.6GB | System packages |
| `/snap` | 423MB | Snapd packages |
| `/var/cache` | 252MB | Apt package cache |
| `/var/log` | 82MB | System logs |

### Docker Images (31GB total)

| Image | Size | Purpose | Keep/Offload |
|-------|------|---------|--------------|
| `openedai-speech` | **12GB** | AI Text-to-Speech | ⚠️ Offload to NAS |
| `ollama` | **8.97GB** | LLM Inference | ⚠️ Offload models to NAS |
| `faster-whisper` | **1.92GB** | Speech-to-Text | Consider cloud API |
| `n8n` | **1.64GB** | Workflow automation | Keep |
| `mas-orchestrator` | **1.26GB** | Python orchestrator | Keep |
| `postgis` | **853MB** | PostGIS database | Keep |
| `grafana` | **873MB** | Monitoring | Keep |
| `mycobrain` | **704MB** | IoT service | Keep |
| `piper-tts` | **596MB** | TTS alternative | Keep |
| `mindex-api` | **536MB** | MINDEX API | Keep |
| `prometheus` | **415MB** | Metrics | Keep |
| `postgres` | **399MB** | PostgreSQL | Keep |
| `website` | **386MB** | Next.js website | Keep |
| `unifi-dashboard` | **302MB** | MYCA dashboard | Keep |
| `qdrant` | **278MB** | Vector DB | Keep |
| `redis` | **131MB** | Cache | Keep |

### Docker Build Cache
- Accumulated **10.34GB** from repeated builds
- Cleared to **0B** after cleanup

---

## Why Docker Build Fills Disk

Each `docker build` creates cached layers:
1. **Base image download** (~200MB for node:20-alpine)
2. **pnpm install** (~1GB for node_modules)
3. **Next.js build** (~500MB for .next folder)
4. **Multi-stage copies** (~200MB)

When builds fail or are interrupted, these layers remain cached.

### Prevention
Add to deployment scripts:
```bash
# After successful build
docker builder prune -f --keep-storage=2GB

# Weekly full cleanup (cron job)
docker system prune -af --volumes --filter "until=168h"
```

---

## Long-Term Architecture Recommendations

### 1. Expand LVM to Use Full Disk
After adding disk space in Proxmox, run:
```bash
sudo pvresize /dev/sda3
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

### 2. Offload AI Models to NAS

The **22GB of AI services** should mount their models from NAS:

| Service | Current Location | Recommended NAS Path |
|---------|------------------|---------------------|
| Ollama models | Docker volume | `/mnt/nas/ai/ollama/models` |
| OpenEDAI voices | Docker volume | `/mnt/nas/ai/openedai/voices` |
| Whisper models | Docker volume | `/mnt/nas/ai/whisper/models` |
| Piper voices | Docker volume | `/mnt/nas/ai/piper/voices` |

### 3. Database Storage Strategy

| Database | Current | Recommended |
|----------|---------|-------------|
| MINDEX PostgreSQL | Docker volume (112MB) | NAS mount for growth |
| MAS PostgreSQL | Docker volume (48MB) | Keep local (small) |
| Qdrant vectors | Docker volume (357B) | NAS mount when grows |
| N8N SQLite | Docker volume (4.7MB) | Keep local (small) |

### 4. Automated Cleanup Cron

Add to VM's crontab:
```bash
# Clean Docker every Sunday at 3 AM
0 3 * * 0 docker system prune -af --filter "until=168h" >> /var/log/docker-cleanup.log 2>&1

# Clean build cache after each deployment
# (Add to deployment script)
docker builder prune -f --keep-storage=2GB
```

---

## Login Session Persistence Issue

**Reported:** Login has no persistence - logs out when navigating to another page.

**Root Cause:** The Supabase session cookie is not being properly stored/read.

**Likely Issues:**
1. `NEXT_PUBLIC_SUPABASE_URL` was pointing to placeholder during build
2. Cookie settings may not match domain
3. Middleware may not be refreshing tokens

**Fix Required:**
1. ✅ Fixed Supabase URL in Dockerfile (done)
2. Need to verify cookie domain in Supabase dashboard matches `sandbox.mycosoft.com`
3. Check middleware for proper session refresh

---

## Action Checklist

### Immediate (Before Shutdown)
- [x] Clear Docker build cache (freed 10GB)
- [x] Document space usage

### During VM Maintenance (COMPLETED Jan 18, 2026)
- [x] Expand virtual disk in Proxmox - **2TB total**
- [x] Upgrade VM memory - **64GB RAM**
- [x] Extend LVM partition to use full disk - **2TB available**
- [ ] Configure NAS mount points

### After VM Restart (COMPLETED Jan 18, 2026)
- [x] Verify disk expansion - **2TB, only 48GB used (3%)**
- [x] Set up automated cleanup cron - **Weekly Docker cleanup**
- [x] Deploy OAuth redirect fix - **commit 94bfc61**
- [x] Container running and healthy - **HTTP 200**
- [ ] Mount NAS volumes for AI models

### Long-Term
- [ ] Move Ollama/OpenEDAI/Whisper models to NAS
- [ ] Implement database backup to NAS
- [ ] Add disk space monitoring alerts (Grafana)

---

## Commands Reference

### Check disk space
```bash
df -h /
docker system df -v
```

### Expand LVM after adding disk
```bash
sudo pvresize /dev/sda3
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

### Clean Docker
```bash
docker builder prune -af          # Clear build cache
docker system prune -af           # Clear everything unused
docker volume prune -f            # Clear unused volumes
```

### Mount NAS (example)
```bash
sudo mount -t nfs nas.local:/volume1/ai /mnt/nas/ai
# Add to /etc/fstab for persistence
```

---

*Report generated by Mycosoft AI Agent*
