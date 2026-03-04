# MYCA Desktop Workstation on VM 191 — Implementation Complete

**Date**: March 3, 2026  
**Status**: Complete  
**Related plan**: `.cursor/plans/myca_desktop_workstation_d6c39a7c.plan.md`

## Overview

VM 191 (192.168.0.191) is now a full MYCA desktop workstation with XFCE, noVNC, XRDP, GUI apps (Chrome, Cursor, VS Code, Discord, Slack, Signal), CLI tools (Claude Code, gh, Playwright, signal-cli, jq, httpie), and AI Python libraries. All 7 phases have been implemented and verified.

## Access

| Method | URL / Target | Notes |
|--------|--------------|-------|
| **noVNC (browser)** | http://192.168.0.191:6080/vnc.html | VNC password: `myca191` |
| **RDP** | 192.168.0.191:3389 | Windows: `mstsc`, connect to that address |
| **SSH** | `ssh mycosoft@192.168.0.191` | Standard SSH |

## Implemented Phases

| Phase | Components |
|-------|------------|
| **1. Desktop** | XFCE, TigerVNC, noVNC, XRDP, websockify |
| **2. Node.js** | Upgraded from v12 to v20.20.0 LTS |
| **3. GUI apps** | Chrome, Cursor (AppImage), VS Code, Discord, Slack, Signal Desktop |
| **4. CLI tools** | Claude Code CLI, GitHub CLI (gh), Playwright, signal-cli, jq, httpie |
| **5. AI libraries** | openai, google-generativeai, anthropic, httpx |
| **6. Firewall** | Ports 3389 (XRDP), 6080 (noVNC) open from 192.168.0.0/24 only |
| **7. Verification** | xrdp active, novnc active, noVNC HTTP 200, Chrome/VS Code/gh installed |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/_install_myca_desktop_191.py` | Full 7-phase install via SSH (Paramiko). Uses `~/.ssh/myca_vm191` or `.credentials.local` for auth. |
| `scripts/_verify_myca_191.py` | Quick verification: node version, paths (chrome, code, gh), service status (xrdp, novnc), noVNC HTTP. |

### Running the installer

```bash
cd MAS/mycosoft-mas
python scripts/_install_myca_desktop_191.py
```

Requires VM 191 reachable and credentials in `.credentials.local` (or SSH key `~/.ssh/myca_vm191`).

## Verification Results

```
node: v20.20.0
chrome: /usr/bin/google-chrome
code: /usr/bin/code
gh: /usr/bin/gh
xrdp: active
novnc: active
noVNC HTTP: 200
```

## Docker (Pre-existing)

VM 191 already runs Docker with: workspace API (8100), n8n (5679), PostgreSQL (5433), Redis (6380). These are the **host** ports from `infra/myca-workspace/docker-compose.yml` (deployed by cloud-init). Internal container ports are 5432/6379; the compose maps host 5433→5432 and 6380→6379 to avoid conflicts. These were not modified by the desktop install.

## Related Documents

- [MYCA N8N Autonomy Complete](./MYCA_N8N_AUTONOMY_COMPLETE_MAR03_2026.md) — n8n workflows, omnichannel, provision script
- [MYCA VM 191 n8n Import Guide](./MYCA_VM191_N8N_IMPORT_GUIDE_MAR03_2026.md) — Workflow import from MAS repo
- [MYCA Autonomous Employee Plan](./MYCA_AUTONOMOUS_EMPLOYEE_PLAN_MAR03_2026.md) — Overall MYCA workspace architecture
