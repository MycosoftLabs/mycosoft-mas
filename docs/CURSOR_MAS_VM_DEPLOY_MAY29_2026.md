# Cursor MAS VM Deploy — May 29, 2026

**Date:** May 29, 2026  
**Status:** In progress / executed by Cursor (not Codex)  
**Related:** `WEBSITE/website/docs/codex-handoffs/CODEX_BLUEGREEN_HANDOFF_MAY29_2026.md`

## Scope split

| Owner | Scope |
|-------|--------|
| **Codex** | Website repo, blue/green on VM 187, Cloudflare purge |
| **Cursor** | MAS VM 188, field heartbeat bridge, Hyphae/Mushroom ops, credentials |

## MAS deploy target (188)

- Pull branch with firmware flash API + device registry updates
- Rebuild `mycosoft/mas-agent:latest` container `myca-orchestrator-new`
- Health: `http://192.168.0.188:8001/health`
- Field bridge: `scripts/install_field_mycobrain_services.py` on 188

## Not deployed via website

- `services/mycobrain/*` on dev PC 241 (COM4 USB)
- Firmware `.bin` artifacts (local `data/firmware_artifacts/`)
- Hyphae live flash until `JETSON_SSH_PASSWORD` confirmed
