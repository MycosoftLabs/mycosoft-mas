# Critical Issue Resolution - initialTimeout Error
**Date**: December 30, 2025, 11:00 PM PST  
**Status**: REBUILDING WITH FULL CACHE CLEAR  

## Issue Summary

### Primary Error
```javascript
ReferenceError: initialTimeout is not defined
    at page-4e94c7fce38048d9.js:1:52949
```

### Secondary Error  
```
GET http://localhost:3000/api/mycobrain/devices 404 (Not Found)
```

## Root Cause Analysis

### Discovery Process
1. **Initial Suspicion**: Old cached build
2. **First Rebuild Attempt**: Used `--no-cache` flag
3. **Result**: Same error persisted
4. **Investigation**: Inspected Docker container filesystem
5. **Finding**: `/api/mycobrain/devices` route NOT present in build
6. **Confirmation**: Source file `app/api/mycobrain/devices/route.ts` EXISTS
7. **Conclusion**: Next.js build not including all routes OR stale Docker layer cache

### Verified Facts
- ✓ Source code has NO `initialTimeout` reference
- ✓ `app/api/mycobrain/devices/route.ts` exists in workspace
- ✓ Docker image has `/api/mycobrain/[port]/*` routes
- ✓ Docker image has `/api/mycobrain/ports` route
- ✗ Docker image MISSING `/api/mycobrain/devices` route
- ✗ Docker image has compiled code with `initialTimeout` bug

## Resolution Strategy

### Phase 1: Complete Cache Elimination (IN PROGRESS)
```bash
# Remove ALL Docker build cache
docker builder prune -af

# Remove container and image
docker stop mycosoft-always-on-mycosoft-website-1
docker rm mycosoft-always-on-mycosoft-website-1
docker rmi mycosoft-always-on-mycosoft-website

# Remove local build cache
rm -rf .next
rm -rf node_modules/.cache

# Rebuild with --pull to get fresh base images
docker-compose build --pull --no-cache mycosoft-website
```

### Phase 2: Verification Checklist
After rebuild completes:
- [ ] Check `/app/.next/server/app/api/mycobrain/devices` exists in container
- [ ] Test `GET http://localhost:3000/api/mycobrain/devices`
- [ ] Navigate to `/natureos/devices` page
- [ ] Verify NO `initialTimeout` error in console
- [ ] Verify MycoBrain devices load correctly

### Phase 3: If Issue Persists
Possible causes:
1. **Dockerfile Issue**: Build copying wrong files
2. **Next.js Config**: Route not being included in standalone build
3. **TypeScript Compilation**: Build error not showing
4. **Git Issue**: Source file not committed/tracked

## Timeline

| Time | Action | Result |
|------|--------|--------|
| 10:00 PM | First rebuild attempt | Failed - same error |
| 10:15 PM | Investigated container | Found missing routes |
| 10:30 PM | Second rebuild | Failed - same error |
| 10:45 PM | Complete cache clear | In progress... |
| 11:00 PM | Third rebuild | **AWAITING RESULT** |

## Technical Details

### Missing Route Structure
**Expected**:
```
/app/.next/server/app/api/mycobrain/
├── [port]/
│   ├── control/route.js
│   ├── sensors/route.js
│   └── peripherals/route.js
├── devices/          ← MISSING!
│   └── route.js      ← MISSING!
├── ports/route.js
└── route.js
```

**Actual** (in container):
```
/app/.next/server/app/api/mycobrain/
├── [port]/
│   ├── control/route.js
│   ├── sensors/route.js
│   └── peripherals/route.js
├── ports/route.js    ← devices folder NOT here
└── route.js
```

### Source Code Verification
```powershell
PS> Test-Path app\api\mycobrain\devices\route.ts
True  ← File EXISTS in source!
```

## Next Steps (If Current Build Fails)

### Option A: Manual Debug
1. Build locally first: `npm run build`
2. Check `.next/standalone` output
3. Verify `devices` route is in build
4. If NOT: Check TypeScript errors
5. If YES: Docker copy issue

### Option B: Simplified Dockerfile
Create minimal test Dockerfile:
```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

### Option C: Development Mode
Run in dev mode temporarily:
```bash
docker run -p 3000:3000 -v $(pwd):/app node:22 npm run dev
```

## Success Criteria
✓ Website loads on http://localhost:3000  
✓ Device Manager page loads without errors  
✓ `/api/mycobrain/devices` returns 200  
✓ MycoBrain device appears in list  
✓ Sensor data displays  
✓ Controls work (LED, Sound)  

## Rollback Plan
If all else fails:
1. Use development server (not Dockerized)
2. Run on host: `npm run dev`
3. MycoBrain service already on host (working)
4. MINDEX in Docker (working)
5. Focus on production Docker later

## Cost Impact
- **Development Time**: 2+ hours
- **Docker Cache**: 5.6GB cleared
- **System Downtime**: Ongoing
- **User Impact**: Website unavailable

## Lessons Learned (So Far)
1. Docker layer caching is aggressive
2. `--no-cache` doesn't clear ALL caches
3. Need `docker builder prune -af` for complete clear
4. Next.js standalone build can be unpredictable
5. Always verify API routes in built container

---
**Status**: Waiting for build completion (ETA: 2-3 minutes)
**Next Update**: After build verification

