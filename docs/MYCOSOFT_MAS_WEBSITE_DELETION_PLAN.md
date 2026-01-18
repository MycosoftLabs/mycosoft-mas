# Mycosoft-MAS Website Deletion Plan

## Problem Statement

The `mycosoft-mas` repository contains a **Next.js website application** in the root directory that is **interfering with the actual Mycosoft Website development** by hijacking port 3000 during development. This website was **NOT requested by the user** and is **NOT the UniFi-style dashboard** they created for MYCA agent management.

## Identified Interfering Website

### Location
- **Root Directory**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`
- **This is a Next.js application** with its own `app/`, `components/`, `package.json`, `next.config.js`

### Structure
```
mycosoft-mas/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Main homepage (shows "Mycosoft MAS" with MYCA, NatureOS, MINDEX links)
│   ├── dashboard/
│   │   └── crep/
│   ├── myca/
│   ├── natureos/
│   ├── mindex/
│   └── api/               # API routes
├── components/            # React components
│   ├── myca-dashboard.tsx
│   └── myca-dashboard-unifi.tsx
├── package.json          # Next.js app package (name: "myca-app")
├── next.config.js        # Next.js configuration
├── tsconfig.json
├── tailwind.config.js
└── ... (other Next.js files)
```

### Homepage Content
The `app/page.tsx` shows:
- Title: "Mycosoft MAS"
- Features: MYCA Orchestrator, NatureOS, MINDEX Search, N8n Workflows
- Links to `/myca`, `/natureos`, `/mindex`, `/n8n`

**This is NOT the actual Mycosoft Website** which should be:
- Located at: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- The real website has the search box, trending topics, CREP dashboard, etc.

## What SHOULD Exist

### UniFi-Style Dashboard for MYCA
- **Location**: `mycosoft-mas/unifi-dashboard/`
- **Purpose**: Agent management dashboard for MYCA (the actual UniFi-style interface)
- **Status**: This should remain, but the directory appears empty

### Actual Mycosoft Website
- **Location**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- **Purpose**: The production Mycosoft website (localhost:3000)
- **Contains**: CREP dashboard, search, trending topics, etc.

## Files/Directories to DELETE

### 1. Next.js Application Files (Root Level)
- `app/` directory (entire Next.js app)
- `components/` directory (unless used by agents)
- `lib/` directory (if Next.js-specific)
- `public/` directory (if Next.js-specific)
- `styles/` directory (if Next.js-specific)
- `package.json` (Next.js app)
- `package-lock.json`
- `next.config.js`
- `next-env.d.ts`
- `tsconfig.json` (if only for Next.js)
- `tailwind.config.js`
- `eslint.config.mjs`
- `middleware.ts` (if Next.js middleware)

### 2. Verify Before Deletion
- Check if any Python agents or services depend on files in these directories
- Check if `components/` contains agent-specific components (not just website UI)
- Check if `app/api/` routes are used by agents or are just website API routes

## Port Conflicts

### Current Port Usage
- **Port 3000**: Should be reserved for the actual Mycosoft Website (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`)
- **Port 3001**: Currently mapped to the mycosoft-mas Next.js app in `docker-compose.yml`
- **Port 3100**: MYCA UniFi Dashboard (should be separate)

### Resolution
- Delete the Next.js app from mycosoft-mas
- Remove port 3001 mapping from `docker-compose.yml` (if it exists)
- Ensure port 3000 is only used by the actual website

## Action Plan

### Step 1: Identify Dependencies
```bash
# Search for imports/references to app/, components/, etc. in Python code
grep -r "from app\." mycosoft_mas/
grep -r "import.*components" mycosoft_mas/
```

### Step 2: Backup (Optional)
```bash
# Create backup of app/ directory before deletion
cp -r app/ app.backup/
```

### Step 3: Delete Interfering Files
Delete the identified directories and files after verifying no dependencies.

### Step 4: Clean Up Docker Compose
Remove any references to the Next.js app service if it exists in `docker-compose.yml`.

### Step 5: Update Documentation
- Remove references to the mycosoft-mas website from README.md
- Update port documentation
- Clarify that mycosoft-mas is for agents/services only

## Verification

After deletion, verify:
1. ✅ Port 3000 is free for the actual website
2. ✅ No build errors from missing app/ directory
3. ✅ Python agents still work
4. ✅ MYCA UniFi Dashboard still accessible (if separate)
5. ✅ Docker containers build successfully
