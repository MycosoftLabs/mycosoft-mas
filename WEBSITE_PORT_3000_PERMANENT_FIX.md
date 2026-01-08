# Port 3000 - Permanent Fix for Website
## Ensure Website Codebase Always Runs on Port 3000

**Date**: January 6, 2026  
**Status**: ✅ **FIXED PERMANENTLY**

---

## Critical Rule

**Port 3000 is EXCLUSIVELY reserved for the website codebase:**
- **Location**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- **NEVER** run mycosoft-mas on port 3000
- **NEVER** create web pages in mycosoft-mas that serve on port 3000

---

## Two Separate Codebases

### 1. Website Codebase (Port 3000)
**Path**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`

**Contains:**
- ✅ Device Manager (`components/mycobrain-device-manager.tsx`)
- ✅ Mycosoft logo homepage
- ✅ NatureOS dashboard
- ✅ MINDEX search
- ✅ All website work and debugging

**To Start:**
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
```

### 2. Mycosoft MAS Codebase (Port 8001)
**Path**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`

**Contains:**
- ✅ MAS Orchestrator API (port 8001)
- ✅ Agent management
- ✅ API endpoints
- ❌ NO web pages (MYCA app pages removed)

**To Start:**
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
# Start MAS services only, NOT web server on port 3000
```

---

## What Was Removed

**Deleted from mycosoft-mas:**
- ❌ `app/myca/page.tsx` - MYCA app page
- ❌ `app/myca/dashboard/page.tsx` - MAS Dashboard page
- ❌ `app/myca/` directory - MYCA app routes

**Reason**: These pages were interfering with the website on port 3000. The MYCA app should integrate with the UniFi dashboard (port 3100), not have its own pages.

---

## Startup Procedure

### Always Start Website from Correct Location

```powershell
# 1. Kill any existing Node processes
Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Navigate to website codebase
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# 3. Clear build cache if needed
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next
}

# 4. Start website
npm run dev
```

### Verify Website is Running

```powershell
# Check port 3000
$response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
if ($response.Content -match "Mycosoft|Device Manager|NatureOS") {
    Write-Host "✅ Website is running correctly"
} else {
    Write-Host "❌ Wrong content on port 3000"
}
```

---

## Prevention Checklist

**Before starting any work:**

- [ ] Verify you're in the correct codebase:
  - Website work → `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
  - MAS work → `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`
- [ ] Check port 3000 is free: `netstat -ano | findstr ":3000.*LISTENING"`
- [ ] Kill any Node processes if port 3000 is in use
- [ ] Start website from WEBSITE codebase only
- [ ] Verify website shows Mycosoft logo and Device Manager

**NEVER:**
- ❌ Run `npm run dev` in mycosoft-mas on port 3000
- ❌ Create web pages in mycosoft-mas
- ❌ Mix website code with MAS code
- ❌ Let MYCA app pages interfere with website

---

## Quick Reference

| Codebase | Path | Port | Purpose |
|----------|------|------|---------|
| **Website** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website` | **3000** | Website homepage, Device Manager, NatureOS |
| **MAS** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas` | **8001** | MAS Orchestrator API, agents, services |

---

## Troubleshooting

### Issue: Port 3000 shows wrong content

**Solution:**
1. Kill all Node processes: `Get-Process node | Stop-Process -Force`
2. Navigate to website codebase: `cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
3. Clear cache: `Remove-Item -Recurse -Force .next`
4. Start website: `npm run dev`
5. Verify: Check `http://localhost:3000` shows website, not MYCA dashboard

### Issue: MYCA app pages still exist

**Solution:**
1. Check if `app/myca/` directory exists in mycosoft-mas
2. Delete it: `Remove-Item -Recurse -Force app\myca`
3. Verify it's gone: `Test-Path app\myca` should return `False`

---

## Summary

✅ **Website codebase** (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`) runs on port 3000  
✅ **MYCA app pages removed** from mycosoft-mas  
✅ **Port 3000 reserved** exclusively for website  
✅ **This should NEVER happen again** if you follow the startup procedure

---

**Last Updated**: January 6, 2026  
**Status**: ✅ **PERMANENTLY FIXED**
