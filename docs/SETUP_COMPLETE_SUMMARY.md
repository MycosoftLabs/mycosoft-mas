# MycoBrain Setup Complete Summary

## ✅ Completed Tasks

### 1. Deprecated Website Files Moved

**Status**: ✅ MOSTLY COMPLETE (app/ directory needs manual intervention)

**Location**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\_deprecated_mas_website\`

**Files Moved**:
- ✅ `components/` (79 files)
- ✅ `lib/` (16 files)
- ✅ `public/` (7 files)
- ✅ `styles/` (empty)
- ✅ `package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.js`, `eslint.config.mjs`, `middleware.ts`
- ⚠️ `app/` (142 files) - **Still exists due to read-only file permissions**

**Action Required**: Manually move `app/` directory:

```powershell
# Option 1: Use PowerShell with admin rights
Get-ChildItem -Path "app" -Recurse | ForEach-Object {
    $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
}
Move-Item -Path "app" -Destination "_deprecated_mas_website\app" -Force

# Option 2: Use robocopy (run as admin)
robocopy "app" "_deprecated_mas_website\app" /E /MOVE /R:5 /W:2
```

**Protection Added**:
- ✅ `.gitignore` updated to exclude `_deprecated_mas_website/`
- ✅ README.md created in deprecated folder explaining why it's deprecated

### 2. Docker Compose Updated

**Status**: ✅ COMPLETE

**Changes**:
- ✅ Removed `myca-app` service from `docker-compose.yml`
- ✅ Port 3001 no longer mapped to deprecated website

**Verification**:
```bash
docker-compose config | grep -i "myca-app"
# Should return nothing
```

---

## 📋 Next Steps Required

### Step 1: Complete App Directory Move

**Manual Action Required**:

1. Open PowerShell **as Administrator**
2. Navigate to: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\`
3. Run:
   ```powershell
   Get-ChildItem -Path "app" -Recurse -Force | ForEach-Object {
       $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
   }
   Move-Item -Path "app" -Destination "_deprecated_mas_website\app" -Force
   ```
4. Verify: `Test-Path "app"` should return `False`

### Step 2: Set Up Cloudflare Tunnel for MycoBrain

**Follow**: `docs/MYCOBRAIN_SETUP_INSTRUCTIONS.md` - Step 3

**Quick Summary**:
1. SSH to VM: `ssh mycosoft@192.168.0.187`
2. Edit `~/.cloudflared/config.yml`
3. Add MycoBrain routes BEFORE catch-all:
   ```yaml
   - hostname: sandbox.mycosoft.com
     service: http://localhost:8003
     path: /api/mycobrain
   
   - hostname: sandbox.mycosoft.com
     service: http://localhost:8003
     path: /api/mycobrain/*
   ```
4. Restart: `sudo systemctl restart cloudflared`

### Step 3: Verify Website API Routes

**Check**: Website API routes are already configured in:
- `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\api\mycobrain\`

**Update Environment Variable**:

In `docker-compose.always-on.yml` (on VM), add to `mycosoft-website` service:
```yaml
environment:
  # ... existing vars ...
  MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003
```

Then restart website:
```bash
docker-compose -f docker-compose.always-on.yml up -d mycosoft-website
```

### Step 4: Ensure Services Persist After Reboot

**Follow**: `docs/MYCOBRAIN_SETUP_INSTRUCTIONS.md` - Step 5

**Quick Summary**:
1. Create systemd service for Docker Compose stack
2. Enable Docker and Cloudflare tunnel services
3. Test by rebooting VM

---

## 📄 Documentation Created

1. ✅ `docs/MYCOBRAIN_SETUP_INSTRUCTIONS.md` - Complete setup guide
2. ✅ `docs/MYCOSOFT_MAS_WEBSITE_ANALYSIS.md` - Analysis of deprecated website
3. ✅ `docs/MYCOSOFT_MAS_WEBSITE_DELETION_SUMMARY.md` - Summary of changes
4. ✅ `docs/SETUP_COMPLETE_SUMMARY.md` - This document

## 🔧 Scripts Created

1. ✅ `scripts/move_deprecated_website.py` - Moves files to deprecated folder
2. ✅ `scripts/update_docker_compose_remove_myca_app.py` - Removes myca-app service
3. ✅ `scripts/setup_mycobrain_cloudflare.py` - Sets up Cloudflare tunnel (needs manual review)
4. ✅ `scripts/check_mycobrain_vm.py` - Checks MycoBrain service status
5. ✅ `scripts/test_mycobrain_connectivity.py` - Tests connectivity

---

## ✅ Verification Checklist

After completing all steps:

- [ ] `app/` directory moved to `_deprecated_mas_website/`
- [ ] `docker-compose.yml` has no `myca-app` service
- [ ] Cloudflare tunnel has MycoBrain routes configured
- [ ] Cloudflare tunnel service is running on VM
- [ ] MycoBrain service is running on VM (port 8003)
- [ ] Website environment variable `MYCOBRAIN_SERVICE_URL` is set
- [ ] Systemd service created for Docker Compose stack
- [ ] Services enabled to start on boot
- [ ] Test: `curl https://sandbox.mycosoft.com/api/mycobrain/health` returns 200
- [ ] Test: `curl http://localhost:3000/api/mycobrain/devices` works locally
- [ ] Test: Services persist after VM reboot

---

## 🆘 Troubleshooting

### Issue: App directory won't move

**Solution**: Run PowerShell as Administrator and remove read-only attributes:
```powershell
Get-ChildItem -Path "app" -Recurse -Force | ForEach-Object {
    $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
}
Move-Item -Path "app" -Destination "_deprecated_mas_website\app" -Force
```

### Issue: Cloudflare tunnel not working

**Solution**: 
1. Check config: `cat ~/.cloudflared/config.yml`
2. Check logs: `sudo journalctl -u cloudflared -f`
3. Verify MycoBrain routes come BEFORE catch-all route
4. Restart: `sudo systemctl restart cloudflared`

### Issue: Website can't reach MycoBrain

**Solution**:
1. Check MycoBrain is running: `docker ps | grep mycobrain`
2. Check website env var: `docker exec mycosoft-website env | grep MYCOBRAIN`
3. Test connectivity: `docker exec mycosoft-website curl http://host.docker.internal:8003/health`

---

## 📞 Quick Reference

**Deprecated Folder**: `_deprecated_mas_website/`  
**VM IP**: 192.168.0.187  
**MycoBrain Port**: 8003  
**Cloudflare Config**: `~/.cloudflared/config.yml`  
**Setup Instructions**: `docs/MYCOBRAIN_SETUP_INSTRUCTIONS.md`
