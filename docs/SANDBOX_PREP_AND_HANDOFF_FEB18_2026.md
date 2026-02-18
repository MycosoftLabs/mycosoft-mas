# Sandbox Prep and Handoff – February 18, 2026

**Purpose:** Single entry point for preparing sandbox live testing on all VMs (outside the development environment). Everything is documented and pushed to GitHub. **Deployment is executed by another agent.**

---

## What Is Prepared

- **Website repo:** Committed and pushed to `main` (MycosoftLabs/website). Latest includes CREP, fungi-compute, test-voice (MYCA Brain flow), unified search, responsive UI, and related fixes.
- **MAS repo:** Documentation and bridge/voice logic. No MAS VM deployment required for Sandbox site; MAS (188), MINDEX (189), and GPU node (190) are expected to already be running.
- **Documentation:** All deployment steps, VM layout, health checks, paths, env vars, and verification are in the docs below.

---

## Documents for the Deploying Agent (Read in Order)

1. **`docs/DEPLOYMENT_HANDOFF_SANDBOX_FEB18_2026.md`**  
   Short checklist and pointer to the full prep doc.

2. **`docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md`**  
   **Single reference** for:
   - VM and GPU node layout (Sandbox 187, MAS 188, MINDEX 189, GPU node 190)
   - What must be running on each host
   - Pre-deploy health check URLs (MAS, MINDEX, Bridge, Sandbox)
   - Full deployment checklist: SSH → pull → stop/rm container → build image → run container **with NAS mount** → verify → purge Cloudflare
   - Paths and image names (`/opt/mycosoft/website`, `mycosoft-website`, `mycosoft-always-on-mycosoft-website:latest`, NAS mount)
   - Test-voice (Bridge 190:8999, MAS 188:8001)
   - Env vars for the website container
   - Post-deploy verification (sandbox.mycosoft.com, assets, API)

---

## GitHub Repos (Source of Truth for Deployment)

- **Website:** https://github.com/MycosoftLabs/website (branch `main`)
- **MAS:** https://github.com/MycosoftLabs/mycosoft-mas (branch `main`)

Deployment must use code from GitHub after pull; do not deploy from local-only changes.

---

## Quick Reference: Live URLs and Ports

| Host      | IP            | Key Service        | Port / URL |
|-----------|---------------|--------------------|------------|
| Sandbox   | 192.168.0.187 | Website            | 3000       |
| MAS       | 192.168.0.188 | Orchestrator       | 8001       |
| MINDEX    | 192.168.0.189 | MINDEX API         | 8000       |
| GPU Node  | 192.168.0.190 | PersonaPlex Bridge | 8999       |
| Live site | —             | sandbox.mycosoft.com | https://sandbox.mycosoft.com/ |

---

## Related Docs

- **VM layout and dev:** `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
- **Dev → Sandbox pipeline:** `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- **Sandbox runbook:** `docs/SANDBOX_DEPLOYMENT_RUNBOOK.md`
- **Voice quick start:** `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`
- **Deploy skill:** `.cursor/skills/deploy-website-sandbox/SKILL.md`
