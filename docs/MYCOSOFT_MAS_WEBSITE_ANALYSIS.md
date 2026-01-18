# Mycosoft-MAS Website Analysis & Deletion Plan

## Executive Summary

The `mycosoft-mas` repository contains a **Next.js website application** that is **interfering with the actual Mycosoft Website** development by hijacking port 3000. This website was created without user authorization and must be deleted.

## Interfering Website Structure

### Root Location
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\
```

### Files and Directories to DELETE

#### 1. Next.js Application Core
- `app/` directory (142 files) - Complete Next.js App Router application
- `components/` directory (79 files) - React components for the website
- `lib/` directory (16 files) - Next.js library utilities
- `public/` directory (7 files) - Static assets
- `styles/` directory (empty but present)

#### 2. Configuration Files
- `package.json` (name: "myca-app", version: 0.1.0)
- `package-lock.json`
- `next.config.js`
- `next-env.d.ts`
- `tsconfig.json`
- `tailwind.config.js`
- `eslint.config.mjs`
- `middleware.ts`

#### 3. Homepage Content (`app/page.tsx`)
Shows:
- Title: "Mycosoft MAS"
- Features: MYCA Orchestrator, NatureOS, MINDEX Search, N8n Workflows
- Stats: "42+ AI Agents", "23 Workflows", "50+ Data Sources", "1M+ Species Records"
- Links to `/myca`, `/natureos`, `/mindex`, `/n8n`

**This is NOT the actual Mycosoft Website.**

## Actual Mycosoft Website

### Correct Location
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\
```

### What It Contains
- Real Mycosoft website with search box
- CREP dashboard (`/dashboard/crep`)
- Trending topics (Lion's Mane Research, Bioremediation, Cordyceps Studies)
- Production website deployed to `localhost:3000` and `sandbox.mycosoft.com`

## Port Configuration

### Current Setup (docker-compose.yml)
- **Port 3000**: Reserved for actual Mycosoft Website (in `docker-compose.always-on.yml`)
- **Port 3001**: Mapped to `myca-app` service (the interfering website)
- **Port 3100**: MYCA UniFi Dashboard (should remain separate)

### Problem
When developing locally, the mycosoft-mas Next.js app can hijack port 3000 if both are running simultaneously.

## Docker Compose Service

### Service Definition (docker-compose.yml, lines 229-235)
```yaml
myca-app:
  build:
    context: .
    dockerfile: Dockerfile.next
    target: runner
  ports:
    - "3001:3000"
```

**This service should be REMOVED** from docker-compose.yml.

## UniFi Dashboard (Should Remain)

### Location
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\unifi-dashboard\
```

### Purpose
- Agent management dashboard for MYCA
- UniFi-style interface for managing agents
- Separate from the interfering website

**Status**: Directory exists but appears empty. This should be preserved/rebuilt if needed.

## API Routes Analysis

The `app/api/` directory contains many routes that may be used by agents:
- `/api/mycobrain/*` - MycoBrain device management
- `/api/natureos/*` - NatureOS integration
- `/api/mas/*` - MAS system endpoints
- `/api/earth-simulator/*` - Earth simulator endpoints

**Action Required**: Verify if these API routes are called by Python agents or if they're only used by the website UI. If agents use them, they may need to be moved elsewhere.

## Deletion Steps

### Step 1: Verify Dependencies
```bash
# Check if Python agents import from app/ or components/
grep -r "from app\." mycosoft_mas/
grep -r "import.*components" mycosoft_mas/
```

### Step 2: Backup (Optional)
```powershell
# Create backup before deletion
Copy-Item -Path "app" -Destination "app.backup" -Recurse
Copy-Item -Path "components" -Destination "components.backup" -Recurse
```

### Step 3: Delete Files
Delete the identified directories and files.

### Step 4: Update docker-compose.yml
Remove the `myca-app` service definition (lines 229-235 or similar).

### Step 5: Update README.md
Remove references to the mycosoft-mas website.

## Verification Checklist

After deletion:
- [ ] Port 3000 is free for actual website
- [ ] No build errors from missing app/ directory
- [ ] Python agents still function
- [ ] Docker containers build successfully
- [ ] No references to `myca-app` in docker-compose.yml
- [ ] Port 3001 mapping removed

## Notes

- The interfering website shows "Mycosoft MAS" homepage, NOT the real website
- User confirmed this was created without authorization
- This conflicts with actual website development on port 3000
- The real website is in `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
