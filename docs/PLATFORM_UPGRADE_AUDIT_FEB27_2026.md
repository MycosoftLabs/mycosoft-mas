# Platform Upgrade Audit

**Date**: February 27, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

Audit of upgrade readiness across the website Node dependency tree and Ubuntu VM package updates, with no changes applied. This document captures current version gaps, engine mismatches, and VM OS package backlog to inform a safe upgrade plan.

## Scope

- Website repo (`WEBSITE/website`) dependency validation and `npm outdated` inventory.
- Ubuntu VMs: Sandbox (187), MAS (188), MINDEX (189).
- Docker runtime versions and running containers per VM.

## Key Findings

### 1) `ikonate` git dependency still resolves via SSH in lockfile

- `package-lock.json` still contains:
  - `node_modules/ikonate.resolved = git+ssh://git@github.com/...`
- This explains the build warning: "skipping integrity check for git dependency ssh://git@github.com/mikolajdobrucki/ikonate.git".
- **Impact**: Docker builds can still hang on SSH key prompts or slow SSH fetches in some environments.

**Evidence**
- `WEBSITE/website/package-lock.json` contains the SSH URL in `resolved` for `ikonate`.

### 2) Node engine mismatch (dependencies require Node 20+)

Build logs show multiple dependencies require Node >= 20 (some >= 22), while the Docker build uses `node:18-alpine`.

**Examples**
- `@supabase/*` require `>=20`
- `cesium` requires `>=20.19.0`
- `vite`, `vitest`, `pdfjs-dist` require Node 20+

**Impact**
- Builds currently succeed but with warnings. Future package updates may break or refuse install on Node 18.

### 3) Website `npm outdated` summary (selected highlights)

**Patch/minor within current major (lower risk, still needs testing)**
- `@deck.gl/*` 9.2.x → 9.2.9
- `@stripe/stripe-js` 8.6.1 → 8.8.0
- `@supabase/supabase-js` 2.90.1 → 2.98.0
- `graphql` 16.12.0 → 16.13.0
- `mapbox-gl` 3.17.0 → 3.19.0
- `maplibre-gl` 5.16.0 → 5.19.0
- `pixi.js` 8.15.0 → 8.16.0
- `react-day-picker` 9.13.0 → 9.14.0
- `sharp` 0.34.4 → 0.34.5
- `stripe` 20.2.0 → 20.4.0
- `swr` 2.3.7 → 2.4.0
- `tailwindcss` 4.1.18 → 4.2.1

**Major jumps (higher risk, API/behavior changes likely)**
- `next` 15.1.11 → 16.1.6
- `react` / `react-dom` 19.0.0 → 19.2.4
- `ai` 4.3.19 → 6.0.103
- `@ai-sdk/openai` 1.3.24 → 3.0.36
- `@langchain/*` 0.3.x → 1.x
- `@vercel/blob` 0.27.3 → 2.3.0
- `framer-motion` 11.18.2 → 12.34.3
- `recharts` 2.15.4 → 3.7.0
- `three` 0.171.0 → 0.183.1
- `zod` 3.25.76 → 4.3.6
- `eslint` 9.39.x → 10.0.x (tooling impact)

### 4) Ubuntu VM updates pending

**Sandbox (187)**
- Ubuntu 24.04.2 LTS, kernel `6.8.0-101-generic`
- **Upgradable packages**: 115
- Docker: 29.1.5 (upgradable to 29.2.1)

**MAS (188)**
- Ubuntu 24.04.2 LTS, kernel `6.8.0-100-generic`
- **Upgradable packages**: 114
- Docker: 29.1.5 (upgradable to 29.2.1)

**MINDEX (189)**
- Ubuntu 22.04.5 LTS, kernel `5.15.0-170-generic`
- **Upgradable packages**: 12
- Docker: 28.2.2 (likely behind 29.x)

## VM Runtime Snapshot

### Sandbox (187)
Running containers include: `mycosoft-website`, `mycorrhizae-api`, `mindex-api`, `n8n`, `postgres`, `redis`, `qdrant`, `earth2-api-gateway`, `e2cc-*`.

### MAS (188)
Running containers include: `myca-orchestrator-new`, `n8n`, `mas-redis`, `mycorrhizae-api`.

### MINDEX (189)
Running containers include: `mindex-api`, `mindex-postgres`, `mindex-qdrant`, `mindex-redis`.

## Risk Assessment

- **Node engine drift** is the primary risk for package upgrades. Many dependencies now require Node 20+, while builds still use Node 18.
- **Major-version JS upgrades** (Next 16, React 19.2, zod 4, recharts 3) are not safe without coordinated migration and testing.
- **VM OS updates** are routine but require maintenance windows and post-update service verification, especially for Docker engine updates.

## Recommendations (No Changes Executed)

1. **Fix `ikonate` lockfile resolution**
   - Update lockfile so `resolved` uses HTTPS (not SSH).
2. **Define target Node version**
   - Decide whether to move Docker base image to Node 20 LTS before upgrading packages.
3. **Stage upgrades in tiers**
   - **Tier 1**: patch/minor updates within current majors.
   - **Tier 2**: major upgrades with migration docs/tests (Next, React, zod, langchain).
4. **VM OS upgrades**
   - Plan OS package updates and Docker engine updates on 187/188; verify services after reboot.
5. **Add compatibility checks**
   - For each major upgrade, run build and smoke tests in sandbox prior to production rollout.

## Related Documents

- `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
