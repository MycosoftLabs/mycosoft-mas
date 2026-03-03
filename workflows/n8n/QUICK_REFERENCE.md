# MYCA n8n Workflows - Quick Reference Guide

## Workflow Matrix

| Workflow | Trigger | Input | Output | Nodes | Status |
|----------|---------|-------|--------|-------|--------|
| Discord to MAS | Discord Event | Messages | Discord DM | 7 | Ready |
| Slack to MAS | Slack Event | Mentions | Slack Thread | 5 | Ready |
| Asana to MAS | Webhook | Tasks | Task Comments | 9 | Ready |
| Signal to MAS | Webhook | SMS | Signal Reply | 5 | Ready |
| WhatsApp to MAS | Webhook | Messages | WhatsApp Reply | 5 | Ready |
| Gmail to MAS | Gmail Event | Email | Email Reply | 7 | Ready |
| Notion Sync | Schedule (3 AM UTC) | Drive Files | Notion + Slack | 6 | Ready |
| Doc Query | Webhook (GET) | Query Param | JSON Response | 5 | Ready |
| Health Check | Schedule (5 min) | Services | Slack Alert | 9 | Ready |
| Response Router | Webhook (POST) | Response | Platform Send | 17 | Ready |

## Endpoint Quick Links

### Input Webhooks
- Discord: Native integration
- Slack: Native integration (app_mention)
- Asana: `POST /webhook/myca/asana`
- Signal: `POST /webhook/myca/signal`
- WhatsApp: `POST /webhook/myca/whatsapp`
- Gmail: Native integration
- Doc Query: `GET /webhook/myca/doc-query?q=search_term`
- Response Router: `POST /webhook/myca/route-response`

### MAS Endpoints
```
POST http://localhost:8001/voice/orchestrator/chat
{
  "message": "user input",
  "session_id": "unique_session_id",
  "platform": "discord|slack|asana|signal|whatsapp|email",
  "user_id": "platform_user_id",
  "channel_id": "platform_channel_id"
}
```

```
POST http://localhost:8001/agents/registry/route/email
{
  "from": "sender@mycosoft.org",
  "to": "schedule@mycosoft.org",
  "subject": "email subject",
  "body": "email body",
  "message_id": "gmail_id",
  "session_id": "unique_id"
}
```

### Health Check Endpoints
- n8n: `http://localhost:5678/healthz`
- MAS: `http://localhost:8001/health`
- Signal: `http://localhost:8089/v1/health`

## Smart Routing Rules

### Asana Assignee Routing
- **Morgan** → Strategic, Budget, Hiring, Legal
- **RJ** → Operations, Processes, Team
- **Garret** → Infrastructure, Architecture, Code

### Response Router Platform Handling
- **Discord**: 2000 char limit → auto-split with pagination
- **Slack**: Thread-aware with thread_ts preservation
- **Email**: Professional signature + formal formatting
- **Signal**: Plain text, no formatting
- **WhatsApp**: WhatsApp message API format

## Error Handling

### Retry Logic (Response Router)
1. **Attempt 1**: Immediate send
2. **Attempt 2**: 2 second delay
3. **Attempt 3**: 4 second delay
4. **Max Retries**: Fallback to Slack #myca-alerts

### Validation
- **Email**: Only @mycosoft.org senders accepted
- **Asana**: Requires MYCA tag on task
- **Slack**: Channel filter on #myca
- **Discord**: Keyword trigger "MYCA" or #myca channel

## Environment Setup

### 1. Set Environment Variables
```bash
export NOTION_FILES_DB_ID="your-notion-db-id"
export NOTION_DOCS_DB_ID="your-notion-db-id"
export ASANA_API_TOKEN="your-asana-token"
export WHATSAPP_API_ENDPOINT="https://..."
export WHATSAPP_API_TOKEN="your-whatsapp-token"
```

### 2. Configure Credentials in n8n
- Discord Bot Token
- Slack App OAuth Token
- Gmail Service Account JSON
- Notion API Key
- Google Drive API Key
- Asana Personal Access Token
- WhatsApp Business API Credentials

### 3. Enable Workflows in Order
1. Health Check (verify services)
2. Doc Query (query API)
3. Notion Sync (data sync)
4. Discord, Slack, Asana, Signal, WhatsApp, Gmail (integrations)
5. Response Router (central hub)

## Testing Checklist

- [ ] Health check passes all 3 services
- [ ] Discord trigger responds to "MYCA" mentions
- [ ] Slack trigger responds to app mentions in #myca
- [ ] Asana webhook receives task events
- [ ] Gmail receives emails to schedule@mycosoft.org
- [ ] Doc query returns results via GET request
- [ ] Notion sync runs at 3 AM UTC
- [ ] Response router forwards to correct platform
- [ ] Signal sends SMS replies
- [ ] WhatsApp sends message replies
- [ ] Error handling triggers on service failures

## Performance Notes

- **Health Check**: Runs every 5 minutes (non-blocking)
- **Notion Sync**: Scheduled for 3 AM UTC (off-peak)
- **Response Router**: Sub-second response time expected
- **Concurrent Platforms**: All integrations can run simultaneously
- **Message Splitting**: Discord responses auto-split to stay under 2000 char

## Troubleshooting

### "Service unhealthy" alert
Check MAS/n8n/Signal health endpoints manually

### Email not received
Verify sender has @mycosoft.org domain

### Task comment not posted
Check Asana API token and task has MYCA tag

### Response never sent
Check Response Router logs and retry counts in #myca-alerts

### Webhook timeouts
Increase timeout in HTTP Request nodes (default 30s)

## File Locations

```
/sessions/sharp-happy-clarke/mnt/MYCOSOFT/12_MYCA_MAS/Workflows/n8n/
├── myca-discord-to-mas.json         (7 nodes)
├── myca-slack-to-mas.json           (5 nodes)
├── myca-asana-to-mas.json           (9 nodes)
├── myca-signal-to-mas.json          (5 nodes)
├── myca-whatsapp-to-mas.json        (5 nodes)
├── myca-gmail-to-mas.json           (7 nodes)
├── myca-notion-sync.json            (6 nodes)
├── myca-doc-query.json              (5 nodes)
├── myca-health-check.json           (9 nodes)
├── myca-response-router.json        (17 nodes)
├── README.md                        (full documentation)
├── MANIFEST.json                    (metadata)
└── QUICK_REFERENCE.md               (this file)
```

## Key Features Summary

✓ Multi-platform message routing
✓ Smart assignee-based routing (Asana)
✓ Domain validation (Email)
✓ Character limit handling (Discord)
✓ Thread preservation (Slack)
✓ Professional formatting (Email)
✓ Health monitoring (5 min intervals)
✓ Document sync (daily)
✓ Real-time search (Notion)
✓ Error handling with exponential backoff
✓ Audit trail with request IDs
✓ Fallback alerting to Slack
