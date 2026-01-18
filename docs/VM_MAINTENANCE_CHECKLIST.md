# VM Maintenance Checklist
**Date:** January 18, 2026  
**VM:** VM103 (192.168.0.187) - Mycosoft Production

---

## BEFORE SHUTDOWN ✅

- [x] Clear Docker build cache (freed 10GB) - **DONE**
- [x] Document disk space usage - **DONE**
- [x] Prevent cloudflared from running on Windows - **DONE**

**Current Status:**
- Disk: 43GB used / 51GB free (47%)
- Docker: Build cache cleared (0B)
- Cloudflared: Stopped and disabled on Windows

---

## DURING VM MAINTENANCE

### Step 1: Expand Virtual Disk in Proxmox

1. **Shutdown VM:**
   ```bash
   # On VM
   sudo shutdown -h now
   ```

2. **In Proxmox Web UI:**
   - Go to VM103 → Hardware → Hard Disk (scsi0)
   - Resize disk from 256GB to desired size (recommend 512GB minimum)
   - Click "Resize disk"

3. **Power on VM** after disk expansion

### Step 2: Expand LVM Partition

After VM is back up, SSH to the VM and run:

```bash
# Upload and run the expansion script
chmod +x expand_lvm.sh
sudo ./expand_lvm.sh
```

**OR manually run:**
```bash
# Resize physical volume
sudo pvresize /dev/sda3

# Extend logical volume
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv

# Resize filesystem
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv

# Verify
df -h /
```

**Expected Result:** LVM should now use the full expanded disk size.

---

## AFTER VM RESTART

### Step 1: Verify Disk Expansion

```bash
df -h /
docker system df
```

Should show increased available space.

### Step 2: Set Up Automated Cleanup Cron

```bash
# Upload and run
chmod +x setup_cleanup_cron.sh
sudo ./setup_cleanup_cron.sh
```

This will:
- Create `/usr/local/bin/docker-cleanup.sh`
- Schedule weekly cleanup every Sunday at 3 AM
- Clean up Docker resources older than 7 days

### Step 3: Verify All Services

```bash
# Check containers
docker ps

# Check Cloudflare tunnel
sudo systemctl status cloudflared

# Test website
curl -I http://localhost:3000

# Test external access
curl -I https://sandbox.mycosoft.com
```

### Step 4: Test OAuth Login Persistence

1. Visit `https://sandbox.mycosoft.com/login`
2. Log in with Google/GitHub
3. Navigate to `/dashboard`
4. Navigate to `/devices`
5. **Verify:** Session should persist across page navigations

If session doesn't persist, check:
- Browser DevTools → Application → Cookies
- Look for `sb-*` cookies from Supabase
- Verify cookie domain is `sandbox.mycosoft.com` (not `localhost`)

---

## LONG-TERM TASKS (After Stabilization)

### Move AI Models to NAS

**Current Location:** Docker volumes  
**Target:** NAS mount at `/mnt/nas/ai/`

**Services to migrate:**
1. **Ollama** (8.97GB) - Models in `/root/.ollama/models`
2. **OpenEDAI Speech** (12GB) - Voices/models directory
3. **Faster Whisper** (1.92GB) - Model cache
4. **Piper TTS** (596MB) - Voice files

**Steps:**
```bash
# Mount NAS (configure in docker-compose.yml)
# Example for Ollama:
volumes:
  ollama-models:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nas.local,rw,nolock,soft
      device: ":/volume1/ai/ollama/models"
```

### Database Backup to NAS

**Current:** Databases in Docker volumes  
**Target:** Daily backups to NAS

**Set up backup cron:**
```bash
# Daily database backup script
0 2 * * * /usr/local/bin/backup-databases.sh
```

### Disk Space Monitoring (Grafana)

Add alert rules for:
- Disk usage > 80%
- Docker images > 30GB
- Build cache > 5GB

---

## SCRIPTS LOCATION

All scripts are in: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\`

1. **expand_lvm.sh** - LVM expansion script
2. **setup_cleanup_cron.sh** - Automated cleanup cron
3. **prevent_cloudflared_windows.ps1** - Windows cloudflared prevention

**To deploy scripts to VM:**
```bash
# From Windows, use Paramiko script or manually SCP
scp scripts/expand_lvm.sh mycosoft@192.168.0.187:~/
scp scripts/setup_cleanup_cron.sh mycosoft@192.168.0.187:~/
```

---

## ROLLBACK PLAN

If something goes wrong during maintenance:

1. **LVM Expansion Failed:**
   - VM should still boot (filesystem not changed, only partition)
   - Revert Proxmox disk size if needed
   - Check logs: `sudo journalctl -xe`

2. **Services Not Starting:**
   - Check Docker: `sudo systemctl status docker`
   - Check containers: `docker ps -a`
   - Restart services: `docker compose up -d`

3. **Website Not Accessible:**
   - Check Cloudflare tunnel: `sudo systemctl status cloudflared`
   - Check website container: `docker logs mycosoft-website`
   - Restart tunnel: `sudo systemctl restart cloudflared`

---

*Checklist created by Mycosoft AI Agent*
