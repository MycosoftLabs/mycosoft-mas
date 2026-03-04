# MYCA VM 191 — n8n Workflow Import Guide

**Date:** Mar 3, 2026  
**n8n URL:** http://192.168.0.191:5679

---

## Workflow files (from branch `claude/autonomous-ai-assistant-2EstA`)

| Workflow          | Repo path                                |
|-------------------|------------------------------------------|
| Daily rhythm      | `workflows/n8n/myca-daily-rhythm.json`   |
| Send email        | `workflows/n8n/myca-send-email.json`     |

**To fetch:** `git fetch origin claude/autonomous-ai-assistant-2EstA` then  
`git checkout origin/claude/autonomous-ai-assistant-2EstA -- workflows/n8n/myca-daily-rhythm.json workflows/n8n/myca-send-email.json`

---

## 5. Import n8n workflows

### Option A: Browser (recommended)

1. **Open n8n**  
   http://192.168.0.191:5679 (or via SSH tunnel from 187/188 if not reachable).

2. **Login:** user `myca`, password from `/opt/myca/.env` → `N8N_PASSWORD` (e.g. `myca_n8n_2026`).

3. **First-time:** Create owner account if prompted.

4. **For each workflow:**
   - Add Workflow (+) → **...** → **Import from File**
   - Select `workflows/n8n/myca-daily-rhythm.json` or `myca-send-email.json` from your local repo
   - Save → toggle **Active** ON

### Option B: CLI (requires owner setup first)

Workflows are already on VM 191 at `/tmp/`. From your machine:

```bash
scp -i ~/.ssh/myca_vm191 workflows/n8n/myca-daily-rhythm.json workflows/n8n/myca-send-email.json mycosoft@192.168.0.191:/tmp/
```

Then SSH and import (n8n API may need owner setup before it accepts requests):

```bash
ssh -i ~/.ssh/myca_vm191 mycosoft@192.168.0.191
# After owner setup, API may work:
curl -u myca:myca_n8n_2026 -X POST http://localhost:5679/api/v1/workflows -H 'Content-Type: application/json' -d @/tmp/myca-daily-rhythm.json
curl -u myca:myca_n8n_2026 -X POST http://localhost:5679/api/v1/workflows -H 'Content-Type: application/json' -d @/tmp/myca-send-email.json
```

### Option C: SSH tunnel for browser access

If 192.168.0.191 is not reachable from your PC:

**PowerShell (recommended):**
```powershell
.\scripts\ssh-tunnel-n8n-vm191.ps1
```

**If `ssh` is not recognized on Windows:** Use full path:
```powershell
& "C:\Windows\System32\OpenSSH\ssh.exe" -i "$env:USERPROFILE\.ssh\myca_vm191" -L 15679:localhost:5679 mycosoft@192.168.0.191
```

**Bash/WSL:**
```bash
ssh -i ~/.ssh/myca_vm191 -L 15679:localhost:5679 mycosoft@192.168.0.191
```

Then open http://localhost:15679

---

## n8n API key and Cursor MCP (for MYCA Cursor/Claude)

When MYCA has her own Claude or Cursor, she will use these.

### API key (public-api)
- **Stored:** `MAS/.credentials.local` → `N8N_API_KEY`
- **Use:** Scripts, API calls, workflow triggers
- **URL:** `N8N_URL=http://192.168.0.191:5679`

### MCP server (Cursor / supergateway)
- **Stored:** User-level `~/.cursor/mcp.json` → `n8n-mcp`
- **Format:** supergateway with `--streamableHttp` and Bearer token
- **Endpoint:** `http://192.168.0.191:5679/mcp-server/http`
- **When using SSH tunnel:** Change URL to `http://localhost:15679/mcp-server/http` and run `scripts/ssh-tunnel-n8n-vm191.ps1` first

### For MYCA’s future Cursor
1. Copy `n8n-mcp` block from `~/.cursor/mcp.json`
2. Ensure VM 191 n8n is reachable (direct 192.168.0.191 or via tunnel)
3. Restart Cursor so it loads the new MCP

---

## Gmail credential (for myca-send-email workflow)

1. In n8n: **Credentials** → **Add Credential**
2. Choose **Gmail OAuth2**
3. Configure for **schedule@mycosoft.org**
4. Complete OAuth flow and save

---

## Status (as of Mar 4, 2026)

- Workflows fetched from branch and SCP'd to VM 191 `/tmp/` ✓
- `myca_n8n` database created ✓
- **n8n fixed:** Added `EXECUTIONS_MODE=regular` and `N8N_RUNNERS_BROKER_PORT=5680` to docker-compose to resolve Task Broker port conflict (crash loop)
- **Manual import via browser is the most reliable path**

---

## Other available workflows (optional)

**n8n/workflows/**
- `myca-intent-orchestrator.json`
- `myca-omnichannel-ingestion.json`
- `myca-proactive-monitor.json`
- `myca-orchestrator.json`
- `myca-business-ops.json`

**workflows/n8n/**
- `myca-response-router.json`
- `myca-discord-to-mas.json`
- `myca-asana-to-mas.json`
- `myca-signal-to-mas.json`
- `myca-slack-to-mas.json`
- `myca-whatsapp-to-mas.json`
