# Instant Website Updates and Faster CI/CD

**Date**: March 15, 2026  
**Status**: Complete  
**Related**: [MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026](./MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026.md), [DEV_TO_SANDBOX_PIPELINE_FEB06_2026](./DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md)

## Overview

Sandbox website deploy was changed so the **image is built in GitHub Actions CI** (with layer cache), pushed to GHCR, and the Sandbox VM **only pulls and restarts** the container. This removes 15–30 minute VM-side Docker builds and most deploy failures. This doc also summarizes how to get faster CI/CD across other repos and VMs.

---

## Sandbox: Build in CI, Deploy = Pull + Restart

### Before
- Push to `main` → workflow SSHs to Sandbox (187) → **on the VM**: `git pull`, then `docker build --no-cache` (15–30 min), then `docker run`.
- Failures: network/timeouts on VM, out-of-memory during build, long feedback loop.

### After
- **Build job (CI):** Checkout, Docker Buildx, GHCR login, build with repo `Dockerfile`, GHA cache (`cache-from/cache-to: type=gha`), push to `ghcr.io/<repo>:sandbox-latest` and `:sandbox-<sha>`.
- **Deploy job:** SSH to Sandbox → (optional) `docker login ghcr.io` if `GHCR_PULL_TOKEN` set → `docker pull` image → stop/rm existing container → `docker run` with same env/mounts (NAS assets, Supabase, MAS/MINDEX URLs) → health check → Cloudflare purge.
- **Result:** Deploy typically **~1–2 minutes** (pull + restart). Build time in CI is separate and benefits from cache on repeat runs.

### Workflow and secrets
- **Workflow:** `WEBSITE/website/.github/workflows/deploy-sandbox-production.yml`
- **Triggers:** Push to `main` (path filters: app, components, lib, public, Dockerfile, package.json, next.config, workflow file) or `workflow_dispatch`.
- **Secrets (website repo):** `SANDBOX_HOST`, `VM_SSH_PRIVATE_KEY`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_API_TOKEN`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`; optional `GHCR_PULL_TOKEN` (PAT with `read:packages`) if the GHCR package is private.

### GHCR image name
- GHCR stores image names in **lowercase**. The deploy step sets `IMAGE_FULL` to the lowercase image (e.g. `ghcr.io/mycosoft/website:sandbox-latest`) so the VM `docker pull` succeeds.

### Local deploy (fast)

To get the same ~1–2 minute deploy from your machine (Cursor, Cloud Code, Perplexity, or manual pushes):

1. **Push to `main`** so the workflow has the code to build.
2. **Trigger the workflow and wait, then purge:**
   ```bash
   # From WEBSITE/website; set token (PAT with repo + workflow permissions)
   export GITHUB_TOKEN=ghp_...
   python _rebuild_sandbox.py --fast
   ```
   With `--production`: same workflow runs (build + deploy); after it completes, the script purges Cloudflare. No VM-side build.

3. **Redeploy last CI-built image only (no new build):**
   ```bash
   # VM: pull existing image, restart container, purge
   export GHCR_PULL_TOKEN=ghp_...   # if GHCR package is private
   python _rebuild_sandbox.py --fast-pull
   ```
   Use when CI already built the image (e.g. after a merge) and you only need to pull and restart on the VM.

**Script:** `WEBSITE/website/_rebuild_sandbox.py`. Without `--fast` or `--fast-pull`, it uses the legacy path (SSH + build on VM, 15–30 min).

---

## Faster CI/CD for Other Repos and VMs

### General principles
1. **Build in CI, not on the VM**  
   Build Docker images in GitHub Actions (or other CI), push to a registry (GHCR, ECR, etc.), then on the VM only pull and restart. Same pattern as Sandbox.

2. **Use layer cache**  
   - GitHub: `cache-from: type=gha`, `cache-to: type=gha,mode=max` so repeat builds are fast.  
   - Order Dockerfile so less-changing layers (deps) come first, app code last.

3. **Path and branch filters**  
   Run deploy (and heavy build) only when relevant paths change; avoid full rebuilds on doc-only or other-repo changes.

4. **Parallelize**  
   Run lint, unit tests, and build in parallel where possible; keep deploy sequential after build.

5. **Smaller images**  
   Multi-stage Dockerfiles, slim base images, and excluding dev dependencies in production reduce build and pull time.

### MAS (VM 188)
- If deploy is “SSH + git pull + docker build on VM”, move to: **build image in CI** (e.g. push to GHCR or existing registry), then VM job: pull image, restart container. Use GHA cache for the image build.
- Keep tests and lint in CI; only run deploy job when needed (e.g. on tag or main with path filters).

### MINDEX (VM 189)
- Same idea: build API (or full stack) image in CI, push to registry, VM pulls and restarts. Database migrations can remain a separate step (run migration job or script after new image is up).

### Other systems
- **GPU node (190), MycoBrain, NatureOS, etc.:** Prefer “build once in CI → push → VM pull/restart” over building on the target machine. Use existing registries or add GHCR/ECR as needed.
- **Website production (if different from Sandbox):** Reuse the same pattern: CI builds image, production VM only pulls and restarts; optionally use a different tag (e.g. `production-latest`).

### Verification
- After any pipeline change: run the workflow once, confirm build uses cache on a second run, and confirm VM deploy is pull + restart only (no `docker build` on the VM).
- Health check and Cloudflare purge (for website) should remain in the deploy step.

---

## CI/CD Secrets Matrix (GitHub Actions)

**Where to set:** Each repo → Settings → Secrets and variables → Actions. Add the following by **name** only (never put real values in code or docs).

| Repo | Secret name | Purpose |
|------|-------------|---------|
| **website** | `SANDBOX_HOST` | VM 187 IP (e.g. 192.168.0.187) |
| **website** | `VM_SSH_PRIVATE_KEY` | SSH private key for user `mycosoft` |
| **website** | `CLOUDFLARE_ZONE_ID` | Zone ID for purge after deploy |
| **website** | `CLOUDFLARE_API_TOKEN` | Token for purge |
| **website** | `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL (if needed at build) |
| **website** | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (if needed at build) |
| **website** | `GHCR_PULL_TOKEN` | (Optional) PAT with `read:packages` for VM pull |
| **MAS (mycosoft-mas)** | `MAS_HOST` | VM 188 IP (e.g. 192.168.0.188) |
| **MAS (mycosoft-mas)** | `VM_SSH_PRIVATE_KEY` | SSH private key for user `mycosoft` |
| **MAS (mycosoft-mas)** | `GHCR_PULL_TOKEN` | (Optional) PAT with `read:packages` for VM pull |
| **MINDEX (mindex)** | `MINDEX_HOST` | VM 189 IP (e.g. 192.168.0.189) |
| **MINDEX (mindex)** | `VM_SSH_PRIVATE_KEY` | SSH private key for user `mycosoft` |
| **MINDEX (mindex)** | `GHCR_PULL_TOKEN` | (Optional) PAT with `read:packages` for VM pull |

**Note:** The same `VM_SSH_PRIVATE_KEY` can be reused across repos if all VMs use the same key. GHCR image names must be **lowercase** when pulling (workflows set `IMAGE_FULL` accordingly).

**deploy-to-vms (MAS repo):** Uses `VM_MAS_HOST`, `VM_MINDEX_HOST`, `VM_SANDBOX_HOST`, `VM_SSH_PRIVATE_KEY`, and optionally `CLOUDFLARE_*`. This workflow is the **fallback** (git pull + build/restart on VM). For **instant** deploys (build in CI, VM pull only), use each repo’s workflow: website → `deploy-sandbox-production.yml`; MAS → `deploy-mas-production.yml`; MINDEX → `deploy-mindex-vm.yml` (in MINDEX repo).

---

## Related Documents

- [MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026](./MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026.md) – Sandbox as production route, tunnel, Supabase/Cloudflare
- [DEV_TO_SANDBOX_PIPELINE_FEB06_2026](./DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md) – Dev-to-sandbox pipeline overview
- [AUTH_DEPLOY_HARDENING_COMPLETE_MAR15_2026](./AUTH_DEPLOY_HARDENING_COMPLETE_MAR15_2026.md) – Auth and CI/CD-first deploy plan
