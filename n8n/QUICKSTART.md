# MYCA Integration Fabric - Quick Start Guide

Get the MYCA n8n Integration Fabric running in 10 minutes.

## What You'll Get

✅ n8n automation server with Postgres & Redis  
✅ 60+ pre-configured integrations (Google, Slack, GitHub, OpenAI, etc.)  
✅ Generic connector for 1200+ other apps  
✅ Hardware control workflows (Proxmox, UniFi, NAS, GPU, UART)  
✅ Security-first design with audit logging and confirmation gates  
✅ Two webhook APIs: `/myca/command` and `/myca/event`

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 4GB RAM minimum
- 10GB disk space
- PowerShell (Windows) or Bash (Linux/Mac)

## Step 1: Bootstrap (2 minutes)

```powershell
# Clone or navigate to MYCA repo
cd path/to/mycosoft-mas/qcd/n8n

# Run bootstrap script
.\scripts\bootstrap.ps1
```

This will:
- Check Docker
- Generate secure random passwords
- Start n8n + Postgres + Redis
- Wait for services to be ready

Output will show:
```
✓ Docker is running
✓ Created .env file
✓ Docker Compose stack started
✓ n8n is ready at http://localhost:5678
```

## Step 2: Access n8n UI (1 minute)

1. Open browser: **http://localhost:5678**
2. Login:
   - Username: `admin`
   - Password: (check output or `cat .env`)
3. You'll see the n8n dashboard

## Step 3: Import Workflows (3 minutes)

**Option A: Manual Import (Recommended)**

1. In n8n UI, click **Workflows** → **Import from File**
2. Import these workflows in order:

**Core workflows (import first):**
- `01_myca_command_api.json` - Main command endpoint
- `01b_myca_event_intake.json` - Event intake endpoint
- `02_router_integration_dispatch.json` - Routes commands to integrations
- `13_generic_connector.json` - HTTP fallback for any API
- `14_audit_logger.json` - Audit trail logging

**Category workflows (import what you need):**
- `03_native_ai.json` - OpenAI, Anthropic, Gemini
- `04_native_comms.json` - Slack, Telegram, Discord (coming soon)
- `05_native_data_storage.json` - Postgres, MongoDB (coming soon)

**Ops workflows (import if using MYCA hardware):**
- `20_ops_proxmox.json` - Proxmox control
- `21_ops_unifi.json` - UniFi network control
- `22_ops_nas_health.json` - NAS health checks
- `23_ops_gpu_job.json` - GPU job runner
- `24_ops_uart_ingest.json` - UART log reader

**Option B: CLI Import (Advanced)**
```bash
npm install -g n8n
cd workflows
n8n import:workflow --input=*.json
```

## Step 4: Configure Credentials (2 minutes)

**Minimum required:**

1. **Postgres** (for audit logging)
   - Settings → Credentials → Add Credential → Postgres
   - Name: `MYCA Postgres`
   - Host: `postgres` (or `localhost` if external)
   - Port: `5432`
   - Database: `n8n`
   - User: `n8n`
   - Password: (from `.env` file)

2. **Telegram Bot** (for alerts - optional but recommended)
   - Talk to [@BotFather](https://t.me/botfather)
   - `/newbot` → follow prompts → get token
   - Settings → Credentials → Add Credential → Telegram
   - Name: `MYCA Alerts`
   - Access Token: (your bot token)

See `credentials/README.md` for more integrations.

## Step 5: Test It (2 minutes)

**Run test suite:**
```powershell
.\scripts\test_api.ps1 -Verbose
```

**Manual test - Command API:**
```powershell
curl -X POST http://localhost:5678/webhook/myca/command `
  -H "Content-Type: application/json" `
  -d '{
    "request_id": "quickstart-001",
    "actor": "morgan",
    "integration": "httpbin",
    "action": "read",
    "params": {
      "endpoint": "/get"
    }
  }'
```

**Expected response:**
```json
{
  "success": true,
  "request_id": "quickstart-001",
  "integration": "httpbin",
  "data": { ... },
  "audit_logged": true
}
```

**Manual test - Event API:**
```powershell
curl -X POST http://localhost:5678/webhook/myca/event `
  -H "Content-Type: application/json" `
  -d '{
    "source": "quickstart",
    "event_type": "test",
    "severity": "info",
    "data": {"message": "Hello MYCA!"}
  }'
```

**Expected response:**
```json
{
  "success": true,
  "event_id": "...",
  "message": "Event received and queued for processing"
}
```

## Step 6: Use It with MYCA

### From Python (MYCA backend)
```python
import requests

def myca_command(integration, action, params, confirm=False):
    """Send command to MYCA Integration Fabric"""
    response = requests.post(
        "http://localhost:5678/webhook/myca/command",
        json={
            "request_id": f"myca-{uuid.uuid4()}",
            "actor": "myca",
            "integration": integration,
            "action": action,
            "params": params,
            "confirm": confirm
        }
    )
    return response.json()

# Example: Read Proxmox VM list
result = myca_command("proxmox", "vm_list", {"node": "pve"})

# Example: Send Telegram alert
result = myca_command("telegram", "send", {
    "text": "Alert from MYCA!",
    "chat_id": "123456789"
})
```

### From JavaScript (MYCA frontend)
```javascript
async function mycaCommand(integration, action, params) {
  const response = await fetch('http://localhost:5678/webhook/myca/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      request_id: `ui-${Date.now()}`,
      actor: 'morgan',
      integration,
      action,
      params
    })
  });
  return response.json();
}

// Example: Read Google Sheet
const result = await mycaCommand('google_sheets', 'read', {
  spreadsheetId: 'abc123',
  range: 'Sheet1!A1:D10'
});
```

## Common Operations

### Control Proxmox VMs
```bash
# List VMs
curl -X POST http://localhost:5678/webhook/myca/command -d '{
  "request_id": "op-001",
  "actor": "you",
  "integration": "proxmox",
  "action": "vm_list",
  "params": {"node": "pve"}
}'

# Create snapshot (requires confirmation)
curl -X POST http://localhost:5678/webhook/myca/command -d '{
  "request_id": "op-002",
  "actor": "you",
  "integration": "proxmox",
  "action": "snapshot",
  "params": {
    "node": "pve",
    "vmid": "100",
    "snapname": "backup-2025-12-17"
  },
  "confirm": true
}'
```

### Query UniFi Network
```bash
curl -X POST http://localhost:5678/webhook/myca/command -d '{
  "request_id": "op-003",
  "actor": "you",
  "integration": "unifi",
  "action": "topology",
  "params": {"site": "default"}
}'
```

### Call Any API (Generic Connector)
```bash
# Example: CoinGecko price check
curl -X POST http://localhost:5678/webhook/myca/command -d '{
  "request_id": "op-004",
  "actor": "you",
  "integration": "coingecko",
  "action": "read",
  "params": {
    "endpoint": "/simple/price",
    "query": {
      "ids": "bitcoin",
      "vs_currencies": "usd"
    }
  }
}'
```

## Monitoring

### Check System Health
```bash
# n8n health
curl http://localhost:5678/healthz

# View logs
docker-compose logs -f n8n

# Check audit trail
docker exec -it myca-n8n-postgres psql -U n8n -c "SELECT * FROM myca_audit ORDER BY timestamp DESC LIMIT 10;"
```

### View Metrics
- Execution history: n8n UI → Executions
- Audit logs: Postgres `myca_audit` table
- JSONL logs: `/mnt/mycosoft-nas/logs/myca_audit.jsonl`

## Next Steps

1. **Add more integrations**: Edit `/registry/integration_registry.json`
2. **Configure production credentials**: See `credentials/README.md`
3. **Enable Vault**: Uncomment vault-agent in `docker-compose.yml`
4. **Set up monitoring**: Enable Prometheus metrics
5. **Read full docs**: See `README.md`

## Troubleshooting

### Workflows not responding
```bash
# Check if workflow is activated
# In n8n UI: Workflows → <workflow> → Activate toggle should be ON

# Check webhook path
docker-compose logs n8n | grep webhook

# Restart n8n
docker-compose restart n8n
```

### Database connection errors
```bash
# Check Postgres is running
docker ps | grep postgres

# Test connection
docker exec myca-n8n-postgres pg_isready -U n8n

# Check credentials
cat .env | grep POSTGRES
```

### "Integration not found" error
```bash
# Check registry file exists
ls -la registry/integration_registry.json

# Check workflow can read it
docker exec myca-n8n ls -la /registry/
```

## Stop/Start

```bash
# Stop all services
docker-compose down

# Start services
docker-compose up -d

# Restart just n8n
docker-compose restart n8n

# View all logs
docker-compose logs -f
```

## Get Help

- **Documentation**: `README.md`, `credentials/README.md`
- **n8n Docs**: https://docs.n8n.io
- **Logs**: `docker-compose logs -f n8n`
- **Test script**: `.\scripts\test_api.ps1 -Verbose`

## Success Checklist

✅ n8n UI loads at http://localhost:5678  
✅ Workflows imported and activated  
✅ Postgres credential configured  
✅ Test suite passes (`test_api.ps1`)  
✅ Command API responds to curl test  
✅ Event API responds to curl test  
✅ Audit logs visible in Postgres  

**You're ready to integrate all the things! 🚀**
