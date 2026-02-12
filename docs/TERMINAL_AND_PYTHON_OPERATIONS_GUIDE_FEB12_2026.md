# Terminal and Python Operations Guide (Feb 12, 2026)

Single reference for what must run, what to kill, and sub-agent execution rules so multiple agents use the same systems without wasting resources.

## 1. What Must Be Running (for MYCA, Search, Multi-Agent)

| System | Required | Where | Check |
|--------|----------|-------|--------|
| **MYCA** | MAS Orchestrator, MINDEX (DB), Ollama | VMs 188, 189 | `curl -s http://192.168.0.188:8001/health` |
| **Search** | MINDEX API, Qdrant, PostgreSQL | VM 189 | `curl -s http://192.168.0.189:8000/` (or /docs) |
| **Multi-Agent** | MAS, Redis | VMs 188, 189 | MAS health includes Redis |
| **Device comms** | MycoBrain Service | Local 8003 | `.\scripts\mycobrain-service.ps1 health` |
| **Cursor context** | Cursor Sync Watcher | Local (no port) | Process: `sync_cursor_system.py --watch` |

## 2. Autostart Services (Local – Keep Running)

| Service | Script | Start | Check |
|---------|--------|--------|--------|
| MycoBrain Service | `services/mycobrain/mycobrain_service_standalone.py` | `.\scripts\mycobrain-service.ps1 start` | `.\scripts\mycobrain-service.ps1 health` |
| Notion Docs Watcher | `scripts/notion_docs_watcher.py` | `.\scripts\notion-sync.ps1 watch-bg` | `.\scripts\notion-sync.ps1 status` |
| Cursor System Sync | `scripts/sync_cursor_system.py --watch` | `python scripts/sync_cursor_system.py --watch` | See Python process list |

Start all missing: `.\scripts\autostart-healthcheck.ps1 -StartMissing`

## 3. Processes to Kill (Zombies / Resource Hogs)

### Zombie one-shot scripts (should have exited)

- `deploy_*.py`, `_deploy_*.py` – deployment scripts
- `chat_with_*.py` – chat scripts left running
- `claude-code-*.py` – deprecated Claude Code experiment
- Inline `paramiko` / SSH one-liners
- Duplicate `sync_cursor_system.py --watch` (keep only one)

### GPU services (kill when not using voice/Earth2)

- PersonaPlex/Moshi (8998), PersonaPlex Bridge (8999)
- Earth2 API (8220), GPU Gateway (8300), PhysicsNeMo (8400)

Kill GPU: `.\scripts\dev-machine-cleanup.ps1 -KillStaleGPU`

### Detection and kill commands

```powershell
# List Python processes with memory
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | 
  Select-Object ProcessId, @{N='MB';E={[math]::Round($_.WorkingSetSize/1MB,1)}}, CommandLine

# Kill zombie one-shot scripts
$zombies = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | 
  Where-Object { $_.CommandLine -match '(deploy_|chat_with_|_deploy_|claude-code-|paramiko)' }
$zombies | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## 4. Sub-Agent Execution Rules

When any agent starts a session:

1. **Zombie check** – Run the zombie detection above; kill matches.
2. **Autostart verification** – Run `.\scripts\autostart-healthcheck.ps1`; use `-StartMissing` if needed.
3. **Resource check** – If the machine is slow, list top RAM (e.g. `Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5`) and kill GPU if present.

Decision matrix:

| Process type | If running | If not running |
|--------------|------------|----------------|
| GPU services | Kill unless user needs voice/Earth2 | Do not start unless requested |
| One-shot scripts | Kill (zombies) | N/A |
| Autostart services | Leave running | Start via healthcheck |
| VM services | N/A (on VMs) | Check VM health |

## 5. References

- **Process registry (always-apply):** `.cursor/rules/python-process-registry.mdc`
- **Process-manager agent:** `.cursor/agents/process-manager.md`
- **Autostart registry:** `.cursor/rules/autostart-services.mdc`
- **Cleanup script:** `scripts/dev-machine-cleanup.ps1 -KillStaleGPU`
