# Petri Dish Simulator Deployment Status

**Date**: February 20, 2026
**Author**: MYCA
**Status**: Partial

## Overview
Deployment status for the Petri Dish Simulator upgrade across MAS, Website, and the
new `petridishsim` service. This records what was pushed to GitHub and which VM
deployments completed.

## GitHub Pushes
- **MAS**: `mycosoft-mas` pushed commit `94e1dfe8b` (petri simulation proxy + docs).
- **Website**: `website` pushed commits `fee79de` and `91b0100` (petri chemical overlays + page wiring).
- **petridishsim**: `petridishsim` pushed commit `2db3799` (FastAPI chemical/segmentation/calibration service).

## Deployments

### MAS VM (192.168.0.188)
- **Status**: Deployed
- **Actions**:
  - Pulled latest `main` on VM.
  - Restarted `mas-orchestrator` systemd service.
- **Health**: `http://192.168.0.188:8001/health` returned `status: degraded` due to
  `collectors` not running (expected for this deploy).

### Website VM (192.168.0.187)
- **Status**: Blocked
- **Issue**: Docker build repeatedly hung due to concurrent `docker build`/BuildKit
  processes running on the VM. Multiple build loops were detected and terminated,
  but the rebuild still did not complete within the deployment window.
- **Actions attempted**:
  - `git reset --hard origin/main`
  - `docker stop`/`docker rm` for `mycosoft-website`
  - `docker build --no-cache` for `mycosoft-always-on-mycosoft-website:latest`
  - `docker run` with NAS mount (not reached)
- **Cloudflare purge**: Not executed (deploy did not complete).

### petridishsim Service
- **Status**: Not deployed
- **Reason**: No VM/container target assigned yet for the `petridishsim` backend service.

## Verification Checklist (Pending)
- [ ] `sandbox.mycosoft.com/apps/petri-dish-sim` reflects new overlays and panels
- [ ] MAS `/api/simulation/petri/*` endpoints reachable on 188
- [ ] `petridishsim` service endpoint reachable at assigned host/port

## Related Documents
- [PETRI_DISH_SIM_UPGRADE_TASK_COMPLETE_FEB20_2026.md](./PETRI_DISH_SIM_UPGRADE_TASK_COMPLETE_FEB20_2026.md)
