# MYCA Integration Fabric (n8n)

Production-grade automation and integration layer for Mycosoft's MYCA Multi-Agent System. This n8n-based integration fabric provides a **modular, registry-driven architecture** that supports 1270+ integrations through native nodes and generic HTTP connectors.

## Overview

The MYCA Integration Fabric serves as MYCA's automation bus, handling:

- **Event Intake** → routing → action execution → audit logging
- **Native integrations** for 60+ popular apps (Google, Slack, GitHub, OpenAI, etc.)
- **Generic connector** for any REST API (covers the long tail of 1200+ integrations)
- **Hardware control** for MYCA infrastructure (Proxmox, UniFi, NAS, GPU, UART)
- **Security-first** design with Vault integration, confirmation gates, and immutable audit trails

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MYCA Command API                            │
│              POST /myca/command (Webhook)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Integration Router                              │
│  • Validates schema                                              │
│  • Loads integration_registry.json                               │
│  • Determines: native node vs generic connector                  │
│  • Enforces confirmation gates                                   │
└────────────┬──────────────────────────────┬─────────────────────┘
             │                              │
      Native Nodes                  Generic Connector
             │                              │
    ┌────────┴────────┐              HTTP Request Node
    │                 │              (any REST API)
    ▼                 ▼                     │
Category Workflows   Ops Workflows          │
 • AI (OpenAI)      • Proxmox              │
 • Comms (Slack)    • UniFi                │
 • DevTools (GitHub)• NAS Health           │
 • Data (Postgres)  • GPU Jobs             │
 • Finance (Stripe) • UART Ingest          │
    │                 │                     │
    └─────────────────┴─────────────────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │   Audit Logger      │
            │  • Postgres         │
            │  • JSONL file       │
            └─────────────────────┘
```

## Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 4GB RAM minimum
- PowerShell 5.1+ (Windows) or Bash (Linux/Mac)

### 1. Bootstrap the Stack

```powershell
# Windows
cd n8n
.\scripts\bootstrap.ps1

# Linux/Mac
cd n8n
bash scripts/bootstrap.sh
```

This will:
1. Check Docker
2. Create `.env` file with secure random passwords
3. Start n8n + Postgres + Redis
4. Wait for n8n to be ready
5. Display access URLs

### 2. Access n8n UI

Open your browser:
- **n8n UI**: http://localhost:5678
- **Username**: `admin`
- **Password**: (check `.env` file or output from bootstrap script)

### 3. Import Workflows

#### Option A: Manual Import (Recommended for first-time setup)
1. In n8n UI, go to **Workflows** → **Import from File**
2. Import workflows in this order:
   - `01_myca_command_api.json` (entrypoint)
   - `01b_myca_event_intake.json` (entrypoint)
   - `02_router_integration_dispatch.json` (core router)
   - `03_native_ai.json` (AI category)
   - `04_native_comms.json` (communications)
   - `05_native_devtools.json` (developer tools)
   - `06_native_data_storage.json` (data & storage)
   - `07_native_finance.json` (finance)
   - `08_native_productivity.json` (productivity)
   - `09_native_utility.json` (utility/glue)
   - `10_native_security.json` (cybersecurity)
   - `13_generic_connector.json` (generic HTTP)
   - `14_audit_logger.json` (audit logging)
   - `20_ops_proxmox.json` through `24_ops_uart_ingest.json` (Ops workflows)

#### Option B: Automated Import (requires n8n CLI)
```bash
npm install -g n8n
n8n import:workflow --input=./workflows/*.json
```

### 4. Configure Credentials

See [credentials/README.md](credentials/README.md) for detailed credential setup.

**Critical credentials to configure:**
- Postgres database connection (for audit logging)
- Telegram bot (for alerts and confirmations)
- API keys for integrations you plan to use

### 5. Test the API

```powershell
# Run test suite
.\scripts\test_api.ps1 -Verbose

# Manual test - Command API
curl -X POST http://localhost:5678/webhook/myca/command `
  -H "Content-Type: application/json" `
  -d '{
    "request_id": "test-001",
    "actor": "morgan",
    "integration": "httpbin",
    "action": "read",
    "params": {
      "endpoint": "/get",
      "method": "GET"
    }
  }'

# Manual test - Event Intake
curl -X POST http://localhost:5678/webhook/myca/event `
  -H "Content-Type: application/json" `
  -d '{
    "source": "test",
    "event_type": "test_event",
    "severity": "info",
    "data": {"message": "Hello from MYCA"}
  }'
```

## Integration Registry

The heart of the system is `/registry/integration_registry.json`, which defines 80+ integrations including:

**Categories:**
- **AI**: OpenAI, Anthropic, Google Gemini, Cohere, Hugging Face, Pinecone
- **Communication**: Slack, Telegram, Discord, Gmail, Twilio, SendGrid
- **Data & Storage**: Postgres, MongoDB, Redis, Google Sheets/Drive, Airtable, S3/GCS
- **Developer Tools**: GitHub, GitLab, Jira, Asana, Trello, CircleCI
- **Finance**: Stripe, QuickBooks, Xero, Square, Wise, CoinGecko
- **Operations**: Proxmox, UniFi, Grafana, Prometheus, Rundeck, GPU/UART/NAS
- **Cybersecurity**: Splunk, Okta, Snyk, Auth0, SecurityScorecard
- **Productivity**: Notion, Google Docs/Calendar/Tasks, Airtable
- **Utility/Glue**: HTTP Request, Code Runner, Cron, Webhook relay

### Adding a New Integration

1. **Add to registry:**
```json
{
  "integration": "my_api",
  "display_name": "My API Service",
  "category": "web",
  "native_node": false,
  "auth_type": "api_key",
  "base_url": "https://api.myservice.com",
  "default_actions": ["read", "create"],
  "risk": "write",
  "confirm_required": true,
  "enabled": true
}
```

2. **If native node exists**: Add handling to appropriate category workflow (e.g., `04_native_comms.json`)

3. **If no native node**: Generic connector will handle it automatically using HTTP Request

4. **Test:**
```bash
curl -X POST http://localhost:5678/webhook/myca/command \
  -d '{"request_id":"test","actor":"you","integration":"my_api","action":"read","params":{"endpoint":"/data"}}'
```

## Workflow Templates

Reusable node patterns are in `/templates/`:

- **oauth2_http_request.json** - OAuth2 API calls
- **api_key_http_request.json** - API key authentication
- **webhook_intake.json** - Secure webhook entrypoint with validation
- **audit_logger.json** - Immutable audit trail
- **error_handler_dlq.json** - Retry logic + dead letter queue
- **confirmation_gate.json** - Two-man rule for destructive actions

Use these templates when creating new workflows to maintain consistency.

## Security

### Credential Management

**NEVER** store secrets in workflow JSON or git. Use one of:

1. **n8n Credentials Manager** (default)
   - Store credentials in n8n UI
   - Reference via credential names
   - Encrypted at rest in Postgres

2. **Vault Integration** (recommended for production)
   - Store secrets in HashiCorp Vault
   - Inject via environment variables at runtime
   - See `credentials/README.md` for setup

3. **Environment Variables**
   - Set in docker-compose.yml or .env
   - Format: `N8N_CREDENTIAL_<TYPE>_<NAME>=<value>`

### Confirmation Gates

Actions with `risk: admin` or `confirm_required: true` require explicit confirmation:

1. Submit command with `confirm: false`
2. System returns 403 with confirmation request
3. User approves (e.g., via Telegram button)
4. Resubmit with `confirm: true`

### Audit Logging

Every action writes to:
- **Postgres** `myca_audit` table (queryable, persistent)
- **JSONL file** `/nas-logs/myca_audit.jsonl` (append-only, backup)

Audit records include:
- Timestamp, request_id, actor, integration, action
- Params hash, response hash (SHA-256)
- Status, duration, error message
- Risk level, confirmation status

Query audits:
```sql
-- Recent actions by actor
SELECT * FROM myca_audit 
WHERE actor = 'morgan' 
ORDER BY timestamp DESC LIMIT 100;

-- Failed actions in last hour
SELECT * FROM myca_audit 
WHERE status = 'error' 
  AND timestamp > NOW() - INTERVAL '1 hour';
```

## MYCA Ops Workflows

Hardware control workflows for MYCA infrastructure:

### Proxmox (`20_ops_proxmox.json`)
```json
{
  "integration": "proxmox",
  "action": "inventory",
  "params": {}
}
// Actions: inventory, snapshot, restore, vm_list, vm_start, vm_stop
```

### UniFi (`21_ops_unifi.json`)
```json
{
  "integration": "unifi",
  "action": "topology",
  "params": {"site": "default"}
}
// Actions: topology, clients, networks, traffic, health
```

### NAS Health (`22_ops_nas_health.json`)
```json
{
  "integration": "mycosoft_nas",
  "action": "health",
  "params": {}
}
// Actions: health, read, backup_verify, space_check
```

### GPU Job Runner (`23_ops_gpu_job.json`)
```json
{
  "integration": "myca_gpu_runner",
  "action": "trigger",
  "params": {
    "job_type": "inference",
    "model": "llama2",
    "input_data": {}
  }
}
```

### UART Ingest (`24_ops_uart_ingest.json`)
```json
{
  "integration": "myca_uart",
  "action": "tail",
  "params": {"lines": 100, "filter": "ERROR"}
}
```

## Maintenance

### Start/Stop Stack
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart n8n only
docker-compose restart n8n

# View logs
docker-compose logs -f n8n
```

### Backup Workflows
```powershell
# Export all workflows to timestamped backup
.\scripts\export.ps1 -Backup
```

### Update n8n
```bash
docker-compose pull n8n
docker-compose up -d n8n
```

### Clear Execution History
```sql
-- Connect to Postgres
docker exec -it myca-n8n-postgres psql -U n8n

-- Clear old executions (older than 30 days)
DELETE FROM execution_entity 
WHERE "startedAt" < NOW() - INTERVAL '30 days';
```

## Monitoring

### Health Checks
- n8n: http://localhost:5678/healthz
- Postgres: `docker exec myca-n8n-postgres pg_isready`
- Redis: `docker exec myca-n8n-redis redis-cli ping`

### Metrics
n8n exposes Prometheus metrics at `/metrics` (enable in settings)

### Logs
```bash
# n8n logs
docker-compose logs -f n8n

# Postgres logs
docker-compose logs postgres

# All services
docker-compose logs -f
```

## Troubleshooting

### Workflows not importing
- Check file permissions on `/workflows` directory
- Ensure JSON is valid (use `jq . < workflow.json`)
- Import manually via n8n UI

### Webhook not responding
- Check workflow is activated (toggle in n8n UI)
- Check webhook path matches: `/webhook/myca/command`
- Test health endpoint first: `curl http://localhost:5678/healthz`

### Database connection errors
- Verify Postgres is running: `docker ps | grep postgres`
- Check credentials in `.env` match docker-compose.yml
- Wait for healthcheck: `docker inspect myca-n8n-postgres | grep Health`

### Generic connector failing
- Check integration registry has correct `base_url`
- Verify API credentials are configured
- Test API directly with curl first
- Check n8n logs for HTTP errors

## Performance Tuning

For high-volume deployments:

1. **Scale execution workers:**
```yaml
# docker-compose.yml
environment:
  - EXECUTIONS_PROCESS=own
  - N8N_PAYLOAD_SIZE_MAX=100
```

2. **Enable Redis queue:**
```yaml
environment:
  - QUEUE_BULL_REDIS_HOST=redis
  - QUEUE_BULL_REDIS_PORT=6379
```

3. **Increase database pool:**
```yaml
environment:
  - DB_POSTGRESDB_POOL_SIZE=20
```

4. **Enable execution pruning:**
```yaml
environment:
  - EXECUTIONS_DATA_PRUNE=true
  - EXECUTIONS_DATA_MAX_AGE=168  # 7 days
```

## Contributing

When adding new workflows or integrations:

1. Follow naming convention: `##_category_name.json`
2. Use workflow templates from `/templates`
3. Add to integration registry
4. Test with `test_api.ps1`
5. Update this README
6. Export and commit workflow JSON

## Support

- **Documentation**: This README and `/docs`
- **n8n Docs**: https://docs.n8n.io
- **MYCA Issues**: See main MYCA repository

## License

Part of Mycosoft MAS project. See root LICENSE file.
