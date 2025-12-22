# n8n Workflow Setup Status

## Date: December 19, 2025

## Summary

All MYCA n8n workflows have been imported and backed up. The workflows are designed to work with the MYCA voice system and dashboard.

## Account Information
- **Email**: morgan@mycosoft.org
- **n8n URL**: http://localhost:5678
- **API Key**: *(do not commit secrets — create/view in n8n UI at `Settings → n8n API`)*
- **API Key Expires**: *(see n8n UI)*

## Imported Workflows (30 total)

### Core MYCA Workflows
- `MYCA: Jarvis Unified Interface` - Main voice assistant entry point
- `MYCA: Master Brain` - AI reasoning and routing
- `MYCA Command API` - API-based commands
- `MYCA Orchestrator` - Workflow orchestration
- `MYCA: Agent Router (Enhanced)` - Agent routing and dispatch
- `MYCA Speech Complete` - Full speech processing pipeline
- `MYCA: Business Ops` - Business operations automation
- `MYCA: System Control` - System management
- `MYCA: Tools Hub` - Tool integrations
- `MYCA: Proactive Monitor` - Background monitoring

### Speech & Voice Workflows
- `Speech: Text to Speech Only` - TTS via ElevenLabs
- `Speech: Transcribe Only` - STT transcription
- `Speech Interface: Complete Pipeline` - Full speech pipeline
- `MYCA Speech Interface v2` - Updated speech interface
- `Speech: Simple Command` - Simple voice commands
- `Speech: Command Turn` - Turn-based voice
- `Speech: Safety & Confirm` - Safety confirmations

### Chat Workflows
- `MYCA Text Chat` - Text-based chat
- `MYCA Voice Chat` - Voice-based chat
- `MYCA Comprehensive Integration` - All-in-one integration

### Operations Workflows
- `Ops: Proxmox Control` - Proxmox VM management
- `Ops: UniFi Control` - UniFi network management
- `Ops: NAS Health Check` - NAS monitoring
- `Ops: GPU Job Runner` - GPU workloads
- `Ops: UART Ingest Reader` - MycoBrain UART data

### Infrastructure Workflows
- `Router: Integration Dispatch` - Integration routing
- `Generic Connector` - Generic integrations
- `Native: AI` - Native AI processing
- `Audit Logger` - Audit logging

## Backup Location

All workflows are backed up to: `n8n/backup/`

These files are safe from Docker container resets and can be re-imported anytime.

## Known Issue

**Webhook Registration**: In n8n v2.0.2, there's an issue where webhooks don't register properly even when workflows are marked as active. This is being investigated.

**Workaround**: The MYCA dashboard has built-in fallback mechanisms:
1. Chat API tries n8n → LiteLLM → Local response
2. TTS API tries ElevenLabs Proxy → ElevenLabs Direct → Browser speech

## Re-Import Workflows

If you need to re-import workflows after a Docker reset:

```powershell
$N8N_API_KEY = "<your-api-key>"
$N8N_URL = "http://localhost:5678"
$WORKFLOWS_DIR = "C:\Users\admin2\.cursor\worktrees\mycosoft-mas\ams\n8n\backup"

$headers = @{
    "X-N8N-API-KEY" = $N8N_API_KEY
    "Content-Type" = "application/json"
}

Get-ChildItem -Path $WORKFLOWS_DIR -Filter "*.json" | ForEach-Object {
    $workflow = Get-Content -Path $_.FullName -Raw | ConvertFrom-Json
    @('id', 'active', 'versionId', 'createdAt', 'updatedAt') | ForEach-Object {
        if ($workflow.PSObject.Properties[$_]) { $workflow.PSObject.Properties.Remove($_) }
    }
    $body = $workflow | ConvertTo-Json -Depth 100 -Compress
    
    try {
        $response = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows" -Method POST -Headers $headers -Body $body
        Write-Host "Imported: $($workflow.name)"
    } catch {
        Write-Host "Failed: $($workflow.name)"
    }
}
```

## Docker Container

The n8n container is running as: `myca-n8n`

Restart: `docker restart myca-n8n`
Logs: `docker logs myca-n8n --tail 50`
