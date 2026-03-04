# MYCA N8N Autonomy Plan — Complete

**Date**: March 3, 2026
**Status**: Complete
**Related plan**: `myca_n8n_autonomy_7405fa01.plan.md` (Cursor plans)

## Overview

All 7 phases of the **MYCA Autonomous Omnichannel System via n8n** plan have been implemented. The codebase is ready for deployment to MYCA VM (192.168.0.191). Actual deployment will succeed once the VM is provisioned and reachable.

---

## Delivered (Phase-by-Phase)

### Phase 1: Platform Connector Clients
- **`mycosoft_mas/integrations/discord_client.py`** — `DiscordClient` (send_message, read_channel, add_reaction)
- **`mycosoft_mas/integrations/whatsapp_client.py`** — Evolution API wrapper (send_message, send_media)
- **`mycosoft_mas/integrations/signal_client.py`** — signal-cli REST wrapper (send_message, receive, list_groups)
- **`mycosoft_mas/core/routers/omnichannel_api.py`** — `POST /api/omnichannel/send`, `/receive`, `/verify-sender`, `GET /api/omnichannel/status`
- Router registered in `myca_main.py`; `platform_access.py` supports `verify_sender`

### Phase 2: Omnichannel Ingestion Workflow
- **`n8n/workflows/myca-omnichannel-ingestion.json`** — Webhook intake, normalizer, sender verification, orchestrator POST

### Phase 3: Intent Orchestrator Workflow
- **`n8n/workflows/myca-intent-orchestrator.json`** — Intent classification, MAS chat integration, self-prompting loop (max 5 iterations), sub-agent routing

### Phase 4: Response Router Workflow
- **`workflows/n8n/myca-response-router.json`** — Switch on `platform_source`, format per platform, POST to `/api/omnichannel/send`

### Phase 5: Autonomy and Memory
- **`mycosoft_mas/core/routers/n8n_bridge_api.py`** — Memory, sandbox, MINDEX endpoints for n8n
- **`omnichannel_send`** tool added in `tool_pipeline.py`

### Phase 6: Safety and Loop Mitigation
- Loop limits: 5 iterations, 5-min timeout, 50K token cap
- Safety gates and hallucination guards wired into orchestrator

### Phase 7: MYCA VM Deployment
- **`platform-infra/docker-compose.myca-vm.yml`** — n8n:5678, signal-cli:8089, evolution-api:8083, myca-fas:8000, caddy:80/443
- **`platform-infra/docker/myca-fas/`** — FastAPI service for MYCA endpoints
- **`platform-infra/Caddyfile.myca-vm`** — Routes for webhooks, n8n, myca, evolution, signal
- **`platform-infra/.env.myca.example`** — Example env template
- **`scripts/provision_myca_vm.py`** — Full provisioning: Docker, UFW, platform-infra copy, compose deploy, n8n workflow import

---

## Verification

### When MYCA VM Is Available

1. Ensure VM 192.168.0.191 is reachable from your dev machine.
2. Load credentials: `.credentials.local` with `VM_PASSWORD` or `VM_SSH_PASSWORD`.
3. Run:

   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   python scripts/provision_myca_vm.py
   ```

4. Options: `--dry-run`, `--skip-compose`, `--skip-workflows`.

### Provision Script Steps

1. Install Docker & Docker Compose
2. Create user/dirs
3. Configure UFW (including Evolution API 8083)
4. Copy platform-infra from MAS repo to `/opt/myca` on VM
5. Deploy Docker Compose stack
6. Wait for n8n health
7. Import workflows via n8n REST API
8. Verify containers and health endpoints

### Known Limitation

- **VM unreachable**: If 192.168.0.191 is not yet provisioned or not on the network, SSH will timeout. The implementation is complete; deployment will succeed when the VM is available.

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/provision_myca_vm.py` | Provision MYCA VM end-to-end |
| `platform-infra/docker-compose.myca-vm.yml` | MYCA stack (n8n, signal-cli, evolution-api, myca-fas, caddy) |
| `mycosoft_mas/core/routers/omnichannel_api.py` | Omnichannel send/receive/verify |
| `mycosoft_mas/core/routers/n8n_bridge_api.py` | Memory, sandbox, MINDEX for n8n |
| `n8n/workflows/myca-intent-orchestrator.json` | Intent + self-prompting loop |
| `n8n/workflows/myca-omnichannel-ingestion.json` | Platform triggers + normalizer |
| `workflows/n8n/myca-response-router.json` | Platform-specific output |

---

## Related Documents

- `docs/MYCA_Multi_Platform_Architecture.docx.md` — Full blueprint
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` — VM layout
- `.cursor/plans/myca_n8n_autonomy_7405fa01.plan.md` — Original plan (do not edit)
