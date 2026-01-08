# Port 3000 - Website Homepage Fix
## Permanent Solution to Prevent MYCA Dashboard from Appearing on Port 3000

**Date**: January 6, 2026  
**Issue**: Port 3000 was showing MYCA Dashboard instead of website homepage  
**Status**: ✅ **FIXED**

---

## Problem

Port 3000 was incorrectly showing the MYCA Dashboard (`/myca/dashboard` or `/myca`) instead of the website homepage (`app/page.tsx`).

---

## Root Causes

1. **Stale Build Cache**: The `.next` directory contained cached builds that may have had incorrect routing
2. **Multiple Node Processes**: Multiple Node.js processes were running, causing port conflicts
3. **Build State Issues**: Next.js build cache may have been serving incorrect routes

---

## Permanent Solution

### 1. Clear Build Cache Before Starting

**Always clear the build cache when starting the website:**

```powershell
# Clear Next.js build cache
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next
    Write-Host "Cleared .next build cache"
}

# Kill any existing Node processes on port 3000
Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Start website
npm run dev
```

### 2. Verify Correct Route is Served

**The root route (`/`) MUST serve `app/page.tsx`:**

- ✅ **Correct**: `app/page.tsx` exports `HomePage` component with "Mycosoft MAS" title
- ❌ **Wrong**: Any redirect to `/myca` or `/myca/dashboard`
- ❌ **Wrong**: `app/myca/page.tsx` or `app/myca/dashboard/page.tsx` on root

### 3. Route Structure

**Correct Next.js App Router structure:**

```
app/
  ├── page.tsx          ← ROOT ROUTE (/) - Website Homepage
  ├── layout.tsx        ← Root Layout
  ├── myca/
  │   ├── page.tsx      ← /myca route - MYCA Dashboard
  │   └── dashboard/
  │       └── page.tsx  ← /myca/dashboard route
  ├── natureos/
  │   └── page.tsx      ← /natureos route
  └── mindex/
      └── page.tsx      ← /mindex route
```

**Port 3000 MUST serve:**
- `/` → `app/page.tsx` (HomePage component)
- `/myca` → `app/myca/page.tsx` (MycaPage component)
- `/myca/dashboard` → `app/myca/dashboard/page.tsx` (DashboardPage component)

---

## Verification Steps

### 1. Check What's Running on Port 3000

```powershell
# Check for processes
netstat -ano | findstr ":3000.*LISTENING"

# Check HTTP response
$response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
$response.Content | Select-String -Pattern "Mycosoft MAS|Platform Features|MASDashboard"
```

**Expected Result:**
- ✅ Contains: "Mycosoft MAS", "Platform Features"
- ❌ Does NOT contain: "MASDashboard", "MycaDashboard"

### 2. Verify Homepage Content

The homepage (`app/page.tsx`) should show:
- ✅ "Mycosoft MAS" title
- ✅ "Platform Features" section
- ✅ Links to MYCA, NatureOS, MINDEX, N8n
- ✅ Stats section (AI Agents, Workflows, etc.)
- ❌ NOT the MYCA Dashboard topology view
- ❌ NOT the MASDashboard component

---

## Startup Script

Create a startup script to ensure correct behavior:

**File**: `start-website.ps1`

```powershell
# Stop any existing Node processes
Write-Host "Stopping existing Node processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Clear build cache
Write-Host "Clearing build cache..." -ForegroundColor Yellow
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next
    Write-Host "✅ Cleared .next build cache" -ForegroundColor Green
}

# Verify port 3000 is free
$port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($port3000) {
    Write-Host "⚠️  Port 3000 is in use. Killing process..." -ForegroundColor Yellow
    Stop-Process -Id $port3000.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start website
Write-Host "Starting website on port 3000..." -ForegroundColor Green
npm run dev
```

---

## Docker Configuration

**If using Docker**, ensure `docker-compose.always-on.yml` has:

```yaml
mycosoft-website:
  build:
    context: .
    dockerfile: Dockerfile
  ports:
    - "3000:3000"  # Website homepage on port 3000
  environment:
    - PORT=3000
    - NODE_ENV=production
```

**The website container MUST serve `app/page.tsx` on the root route.**

---

## Troubleshooting

### Issue: Still seeing MYCA Dashboard on port 3000

**Solution:**
1. Kill all Node processes: `Get-Process node | Stop-Process -Force`
2. Clear build cache: `Remove-Item -Recurse -Force .next`
3. Verify `app/page.tsx` exists and exports `HomePage`
4. Restart: `npm run dev`
5. Test: `Invoke-WebRequest http://localhost:3000` and check content

### Issue: Port 3000 is already in use

**Solution:**
```powershell
# Find process using port 3000
$process = Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object -First 1
if ($process) {
    Stop-Process -Id $process.OwningProcess -Force
}
```

### Issue: Website shows wrong content

**Solution:**
1. Check `app/page.tsx` - must export `HomePage` component
2. Check `app/layout.tsx` - must wrap children correctly
3. Clear `.next` directory
4. Restart dev server
5. Hard refresh browser (Ctrl+Shift+R)

---

## Prevention Checklist

Before starting the website, always:

- [ ] Kill any existing Node processes
- [ ] Clear `.next` build cache if issues occur
- [ ] Verify port 3000 is free
- [ ] Start with `npm run dev` (not `npm start` in production mode)
- [ ] Test `http://localhost:3000` shows homepage, not MYCA dashboard
- [ ] Verify `app/page.tsx` is the root route handler

---

## File Locations

- **Website Homepage**: `app/page.tsx` (exports `HomePage`)
- **MYCA Dashboard**: `app/myca/page.tsx` (exports `MycaPage`)
- **MYCA Dashboard Detail**: `app/myca/dashboard/page.tsx` (exports `DashboardPage` with `MASDashboard`)

**CRITICAL**: Only `app/page.tsx` should be served on port 3000 root route (`/`).

---

## Summary

✅ **Port 3000 = Website Homepage (`app/page.tsx`)**  
✅ **Port 3001 = MYCA App (if needed, but should integrate with UniFi dashboard)**  
✅ **`/myca` = MYCA Dashboard route (accessible via navigation, not root)**

**This should NEVER be a recurring issue if:**
1. Build cache is cleared when needed
2. Only one Node process runs the website
3. `app/page.tsx` correctly exports the homepage component
4. No redirects or rewrites send `/` to `/myca`

---

**Last Verified**: January 6, 2026  
**Status**: ✅ Working correctly
