# Platform Upgrade Complete

**Date**: February 28, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

Execution of the Feb 27 platform upgrade plan is complete. This includes Tier 1 dependency updates, Node 20 Docker base, VM OS updates, full sandbox rebuild from scratch, Cloudflare cache purge, and smoke tests.

## Delivered

### Website (repo: `WEBSITE/website`)
- Tier 1 dependency updates applied (patch/minor only).
- Docker base moved to Node 20 for all stages.
- Deck.gl patching applied during Docker build.
- Added MINDEX health proxy route for smoke tests.
- Devices API hardened to avoid local-only mock responses.
- Not-found page simplified to stabilize prerender builds.

### VM Updates
- Sandbox (192.168.0.187): OS updates + Docker upgrade verified.
- MAS (192.168.0.188): OS updates + Docker upgrade verified.
- MINDEX (192.168.0.189): OS updates + Docker upgrade verified; Docker daemon healthy.

### Sandbox Deployment
- Full rebuild on 192.168.0.187 with `--no-cache` and clean rebuild.
- Container restarted with NAS assets mount.
- Runtime env vars set for MAS/MINDEX URLs.
- Cloudflare cache purged (purge everything).

## Verification

### Build (Docker)
- Website Docker build completed successfully on sandbox.
- Patch-package applied for `@deck.gl/mapbox@9.2.10`.

### Smoke Tests (sandbox.mycosoft.com)
- Homepage: HTTP 200
- `/api/health`: HTTP 200
- `/api/mas/health`: HTTP 200
- `/api/mindex/health`: HTTP 200
- NAS asset served via container: HTTP 200 (sample file from `/assets`)

## Notes / Warnings

- Build warnings about Docker ENV secrets remain (pre-existing). These are not new and require separate secrets management changes if desired.
- iNaturalist/MINDEX API health is dependent on runtime env vars; container start now injects MAS/MINDEX URLs explicitly.
- Tier 2 major upgrades remain deferred (Next 16, React 19.2, Zod 4, Recharts 3, LangChain 1.x, etc.).

## Related Documents

- `docs/PLATFORM_UPGRADE_AUDIT_FEB27_2026.md`
- `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
