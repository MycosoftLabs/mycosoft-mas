# Compounds Bug Fix and Deployment Handoff – February 19, 2026

**Date**: February 19, 2026  
**Status**: Complete – Ready for Deploy  
**Repo**: MycosoftLabs/website  
**Commit**: `d208b65` (pushed to `main`)

## Overview

Bug fix: species detail page was attempting to call MINDEX directly from the client using `process.env.NEXT_PUBLIC_MINDEX_API_URL` / `MINDEX_API_URL`, which are server-only in Next.js. This caused compounds fetch to fail in production when MINDEX runs on a different host (VM 189).

**Fix:** Compounds are now fetched via a website API route (`/api/compounds/species/[id]`) that proxies to MINDEX server-side. No client env vars needed.

## Changes Pushed

| File | Change |
|------|--------|
| `app/api/compounds/species/[id]/route.ts` | **New** – Server-side proxy to MINDEX `/api/mindex/compounds/for-taxon/{taxon_id}` |
| `app/ancestry/species/[id]/page.tsx` | Compounds fetch via `/api/compounds/species/${species.id}` only; removed `getFallbackCompounds` (no-mock-data) |

The commit also includes other staged work (SporeBase, neuromorphic UI, MycoBrain, etc.). Full deploy covers all of it.

## Deployment (For Another Agent)

Code is pushed. Use the standard website deploy flow:

1. **Reference**: `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` (full checklist)
2. **VM**: Sandbox 192.168.0.187
3. **Steps**: SSH → pull → rebuild Docker image → run container **with NAS mount** → purge Cloudflare

### Quick Deploy Commands (Sandbox VM)

```bash
ssh mycosoft@192.168.0.187
cd /opt/mycosoft/website
git fetch origin && git reset --hard origin/main
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

Then **purge Cloudflare cache** (Purge Everything).

### Env (Website Container)

The compounds API route uses `MINDEX_API_URL` (server-only). Ensure the website container has:

- `MINDEX_API_URL=http://192.168.0.189:8000` (or wherever MINDEX runs)

## Verification

1. **Species page compounds**: Visit `https://sandbox.mycosoft.com/ancestry/species/{uuid}` (MINDEX taxon UUID). Compounds tab should load data when MINDEX has compound associations; otherwise empty (no mock).
2. **API direct**: `GET /api/compounds/species/{taxon_id}` returns `{ compounds: [...], source: "mindex" }` or empty on 404/error.

## Related Documents

- `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` – Full deploy checklist
- `docs/DEPLOYMENT_HANDOFF_SANDBOX_FEB18_2026.md` – Short handoff
- `docs/API_CATALOG_FEB04_2026.md` – API catalog (add `/api/compounds/species/[id]` if not present)
