# MYCA n8n Workflows - Complete Index

## Start Here

1. **First Time Setup**: Read `SUMMARY.txt`
2. **Configuration Guide**: See `README.md`
3. **Quick Operations**: Use `QUICK_REFERENCE.md`
4. **Technical Details**: Check individual workflow JSON files

---

## File Structure

```
/sessions/sharp-happy-clarke/mnt/MYCOSOFT/12_MYCA_MAS/Workflows/n8n/
│
├── 📄 WORKFLOW JSON FILES (10 files - all production ready)
│   ├── myca-discord-to-mas.json         ← Discord integration
│   ├── myca-slack-to-mas.json           ← Slack integration
│   ├── myca-asana-to-mas.json           ← Asana with smart routing
│   ├── myca-signal-to-mas.json          ← Signal SMS integration
│   ├── myca-whatsapp-to-mas.json        ← WhatsApp integration
│   ├── myca-gmail-to-mas.json           ← Email with validation
│   ├── myca-notion-sync.json            ← Daily sync to Notion
│   ├── myca-doc-query.json              ← Document search API
│   ├── myca-health-check.json           ← Service monitoring
│   └── myca-response-router.json        ← Central response hub
│
├── 📚 DOCUMENTATION FILES
│   ├── INDEX.md                         ← This file
│   ├── SUMMARY.txt                      ← Executive summary
│   ├── README.md                        ← Full documentation
│   ├── QUICK_REFERENCE.md               ← Operator's guide
│   └── MANIFEST.json                    ← Metadata & stats
│
└── 📋 YOU ARE HERE
```

---

## Workflow Quick Links

### Communication Platforms (5 workflows)

**Discord to MAS** - `myca-discord-to-mas.json`
- Triggers on "MYCA" mentions or #myca channel messages
- Posts to MAS Orchestrator
- Auto-splits responses >2000 characters
- 7 nodes | Input: Discord Events | Output: Discord Messages

**Slack to MAS** - `myca-slack-to-mas.json`
- Triggers on app mentions in channels
- Preserves threading with thread_ts
- 5 nodes | Input: Slack Events | Output: Slack Messages

**Asana to MAS** - `myca-asana-to-mas.json`
- Webhook trigger on task creation/updates with MYCA tag
- Smart routing by assignee (Morgan/RJ/Garret)
- Posts response as task comment
- 9 nodes | Input: Webhook | Output: Asana Comments

**Signal to MAS** - `myca-signal-to-mas.json`
- Webhook from Signal REST API
- Plain text message support
- 5 nodes | Input: Webhook | Output: Signal SMS

**WhatsApp to MAS** - `myca-whatsapp-to-mas.json`
- Webhook from WhatsApp Business API
- WhatsApp-formatted responses
- 5 nodes | Input: Webhook | Output: WhatsApp Messages

### Email & Routing (2 workflows)

**Gmail to MAS** - `myca-gmail-to-mas.json`
- Gmail trigger for schedule@mycosoft.org
- Domain validation (@mycosoft.org only)
- Professional email responses with signature
- 7 nodes | Input: Gmail Events | Output: Email Replies

**Response Router** - `myca-response-router.json`
- Central hub for distributing responses to all platforms
- Platform-aware formatting (Discord splits, Slack threads, etc.)
- Error handling with 3-attempt retry + exponential backoff
- Fallback alerts to Slack #myca-alerts
- 17 nodes | Input: Webhook (POST) | Output: All Platforms

### Data & Monitoring (3 workflows)

**Notion Sync** - `myca-notion-sync.json`
- Daily schedule (3 AM UTC)
- Syncs Google Drive files modified in last 24 hours
- Updates Notion database
- Posts summary to Slack #myca-logs
- 6 nodes | Input: Schedule (Cron) | Output: Notion + Slack

**Document Query** - `myca-doc-query.json`
- REST API at `/webhook/myca/doc-query?q=search_term`
- Real-time search across Notion documents
- Returns JSON with titles, links, snippets
- 5 nodes | Input: Webhook (GET) | Output: JSON Response

**Health Check** - `myca-health-check.json`
- Runs every 5 minutes
- Checks n8n, MAS, Signal endpoints
- Alerts to Slack #myca-alerts on failures
- Logs all results
- 9 nodes | Input: Schedule (5 min) | Output: Slack Alerts + Logs

---

## Key Configurations

### API Endpoints

```
MAS Orchestrator:          http://localhost:8001/voice/orchestrator/chat
Email Registry Route:      http://localhost:8001/agents/registry/route/email
Voice Registry Route:      http://localhost:8001/agents/registry/route/voice
Signal API:                http://localhost:8089
n8n Health:                http://localhost:5678/healthz
```

### Webhook Paths

```
Base:                      http://localhost:5678/webhook/myca/
Asana:                     POST /webhook/myca/asana
Signal:                    POST /webhook/myca/signal
WhatsApp:                  POST /webhook/myca/whatsapp
Document Query:            GET  /webhook/myca/doc-query?q=query
Response Router:           POST /webhook/myca/route-response
```

### Slack Channels

```
#myca            - Main workflow messages and responses
#myca-logs       - Daily Notion sync summaries
#myca-alerts     - Error and failure notifications
```

---

## Getting Started (3 Steps)

### Step 1: Prepare Environment
```bash
# Set required environment variables
export NOTION_FILES_DB_ID="your-id"
export NOTION_DOCS_DB_ID="your-id"
export ASANA_API_TOKEN="your-token"
export WHATSAPP_API_ENDPOINT="your-endpoint"
export WHATSAPP_API_TOKEN="your-token"
```

### Step 2: Import Workflows
- Open n8n
- Import all 10 JSON files from this directory
- Configure platform credentials (Discord, Slack, Gmail, etc.)

### Step 3: Enable in Order
1. Health Check (verify services)
2. Doc Query (test search)
3. Notion Sync (test data)
4. Discord, Slack, Asana, Signal, WhatsApp, Gmail (test each)
5. Response Router (enable last)

---

## Performance Specs

| Workflow | Trigger | Frequency | Nodes | Size |
|----------|---------|-----------|-------|------|
| Discord | Event | On mention | 7 | 5.5 KB |
| Slack | Event | On mention | 5 | 4.1 KB |
| Asana | Webhook | On task update | 9 | 6.9 KB |
| Signal | Webhook | On message | 5 | 3.8 KB |
| WhatsApp | Webhook | On message | 5 | 4.2 KB |
| Gmail | Event | On email | 7 | 5.5 KB |
| Notion Sync | Schedule | 3 AM UTC | 6 | 3.9 KB |
| Doc Query | Webhook | On demand | 5 | 3.1 KB |
| Health Check | Schedule | Every 5 min | 9 | 5.4 KB |
| Response Router | Webhook | On POST | 17 | 12 KB |

---

## Troubleshooting

### Issue: JSON Import Fails
**Solution**: Ensure all 10 files are valid JSON (use online validators if needed)

### Issue: Service Health Check Fails
**Solution**: Verify MAS (8001), n8n (5678), and Signal (8089) are running

### Issue: Email Not Received
**Solution**: Check sender domain is @mycosoft.org (enforced validation)

### Issue: Asana Comment Not Posted
**Solution**: Verify Asana API token and task has MYCA tag

### Issue: Response Never Reaches Platform
**Solution**: Check Slack #myca-alerts for retry failures and logs

---

## Security Notes

1. **Domain Validation**: Email workflow only accepts @mycosoft.org senders
2. **Token Management**: All API tokens in environment variables, never hardcoded
3. **Error Handling**: Responses sanitized to prevent data leakage
4. **Audit Trail**: Request IDs logged for all operations
5. **Rate Limiting**: Health checks spaced 5 minutes apart

---

## Support Resources

- **Full Documentation**: `README.md`
- **Quick Reference**: `QUICK_REFERENCE.md`
- **Metadata**: `MANIFEST.json`
- **Summary**: `SUMMARY.txt`

---

## Contact & Info

- **Project**: MYCA Multi-Agent System
- **Component**: n8n Workflow Integrations
- **Version**: 1.0.0
- **Status**: Production Ready
- **Created**: 2026-03-03
- **Total Files**: 12 (10 workflows + 3 docs)
- **Total Size**: 88 KB
- **Node Count**: 63

---

**START WITH**: Read `SUMMARY.txt` for a 2-minute overview, then `README.md` for full details.
