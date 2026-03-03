# MYCA Multi-Agent System - n8n Workflows

Production-ready n8n workflow definitions for the MYCA Multi-Agent System. All workflows are configured to integrate with the MAS Orchestrator and various communication platforms.

## Configuration

### Required Environment Variables
- `NOTION_FILES_DB_ID` - Notion database ID for file syncing
- `NOTION_DOCS_DB_ID` - Notion database ID for document queries
- `ASANA_API_TOKEN` - Asana API token for task updates
- `WHATSAPP_API_ENDPOINT` - WhatsApp API endpoint URL
- `WHATSAPP_API_TOKEN` - WhatsApp API authentication token

### Core Endpoints
- **MAS Orchestrator**: `http://localhost:8001/voice/orchestrator/chat`
- **Email Registry Route**: `http://localhost:8001/agents/registry/route/email`
- **Voice Registry Route**: `http://localhost:8001/agents/registry/route/voice`
- **Signal REST API**: `http://localhost:8089`
- **n8n Health**: `http://localhost:5678/healthz`

## Workflows

### 1. myca-discord-to-mas.json
**Purpose**: Discord message routing to MAS Orchestrator

**Flow**:
- Discord trigger listens for messages mentioning MYCA or in #myca channel
- Parses message, user, and channel information
- POSTs to MAS Orchestrator with platform:"discord"
- Formats response respecting 2000 character Discord limit
- Splits long responses across multiple messages
- Sends responses back to originating channel

**Nodes**: 6 | **Type**: Integration | **Trigger**: Discord Event

---

### 2. myca-slack-to-mas.json
**Purpose**: Slack mention/message routing to MAS Orchestrator

**Flow**:
- Slack event trigger (app_mention + message.channels)
- Parses text, user, channel, and thread information
- POSTs to MAS Orchestrator with platform:"slack"
- Formats response with threading support
- Posts reply in same thread if original message was threaded
- Respects Slack's formatting and threading model

**Nodes**: 5 | **Type**: Integration | **Trigger**: Slack Event

---

### 3. myca-asana-to-mas.json
**Purpose**: Asana task automation with smart routing

**Flow**:
- Webhook receives task create/update events with MYCA tag
- Parses task name, description, assignee, and project
- POSTs to MAS Orchestrator with platform:"asana"
- **Smart Routing by Assignee**:
  - Morgan → Strategic/Budget/Hiring/Legal topics
  - RJ → Operations/Processes/Team topics
  - Garret → Infrastructure/Architecture/Code topics
- Adds MAS response as comment on task
- Updates task with routed response

**Nodes**: 8 | **Type**: Integration | **Trigger**: Webhook

---

### 4. myca-signal-to-mas.json
**Purpose**: Signal messenger integration with SMS-style messaging

**Flow**:
- Webhook receives messages from Signal REST API
- Parses sender phone number and message text
- POSTs to MAS Orchestrator with platform:"signal"
- Formats response as plain text
- Sends reply back via Signal REST API to sender

**Nodes**: 5 | **Type**: Integration | **Trigger**: Webhook

---

### 5. myca-whatsapp-to-mas.json
**Purpose**: WhatsApp business messaging integration

**Flow**:
- Webhook receives messages from WhatsApp/Baileys
- Parses sender number and message content
- POSTs to MAS Orchestrator with platform:"whatsapp"
- Formats response for WhatsApp's text message format
- Sends reply via WhatsApp API with proper recipient formatting

**Nodes**: 5 | **Type**: Integration | **Trigger**: Webhook

---

### 6. myca-gmail-to-mas.json
**Purpose**: Email routing with domain validation

**Flow**:
- Gmail trigger watches for emails to schedule@mycosoft.org
- Parses from, to, subject, body, and timestamp
- **Domain Filter**: Only processes @mycosoft.org senders
- POSTs to email registry route with full context
- Formats professional email response with MYCA signature
- Sends reply from schedule@mycosoft.org to sender

**Nodes**: 7 | **Type**: Integration | **Trigger**: Gmail Event

---

### 7. myca-notion-sync.json
**Purpose**: Daily document sync from Google Drive to Notion

**Flow**:
- Cron trigger runs daily at 3 AM UTC
- Lists Google Drive files modified in last 24 hours
- Parses file metadata (name, type, modified time, owner)
- Updates Notion database with file records
- Creates summary text of all modified files
- Posts summary to Slack #myca-logs channel

**Nodes**: 6 | **Type**: Sync | **Trigger**: Schedule (3 AM UTC)

---

### 8. myca-doc-query.json
**Purpose**: Real-time document search API

**Flow**:
- Webhook receives GET requests at `/webhook/myca/doc-query`
- Extracts query parameter from request
- Searches Notion database for matching documents
- Formats results with titles, links, and snippets
- Returns JSON response with search results and metadata

**Nodes**: 5 | **Type**: Query | **Trigger**: Webhook (GET)

---

### 9. myca-health-check.json
**Purpose**: System health monitoring with alerting

**Flow**:
- Cron trigger runs every 5 minutes
- Parallel health checks:
  - n8n: `GET http://localhost:5678/healthz`
  - MAS: `GET http://localhost:8001/health`
  - Signal: `GET http://localhost:8089/v1/health`
- Evaluates response codes (200 = healthy)
- On failure: Formats alert message with failed services
- Posts alert to Slack #myca-alerts channel
- Logs all results for monitoring

**Nodes**: 10 | **Type**: Monitoring | **Trigger**: Schedule (5 min)

---

### 10. myca-response-router.json
**Purpose**: Central response distribution hub with intelligent formatting

**Flow**:
- Webhook receives POST with response and platform_source
- Parses routing request body parameters
- **Smart Platform Switch**:
  - Discord: Splits responses respecting 2000 char limit
  - Slack: Uses thread_ts for threaded responses
  - Email: Applies professional signature
  - Signal: Plain text formatting
  - WhatsApp: WhatsApp-compatible message structure
- **Error Handling**:
  - Catches send failures
  - Retries up to 3 times with exponential backoff (1s, 2s, 4s)
  - Falls back to Slack #myca-alerts alert on max retries
- Unhandled platforms post warning to #myca-alerts

**Nodes**: 13 | **Type**: Core Routing | **Trigger**: Webhook (POST)

---

## Integration Points

### Inbound
- Discord: Event subscriptions
- Slack: Event subscriptions + webhooks
- Asana: Webhook triggers on task updates
- Signal: REST API webhooks
- WhatsApp: Webhook from business API
- Gmail: Trigger on new messages
- Google Drive: API queries

### Outbound
- MAS Orchestrator (8001): Chat, routing endpoints
- Discord: Message sending
- Slack: Message posting, threading
- Asana: Task comments
- Signal: Message delivery
- WhatsApp: Message API
- Gmail: Reply sending
- Notion: Database updates and queries
- Google Drive: File metadata queries

## Security Considerations

1. **Domain Validation**: Email workflow filters to @mycosoft.org only
2. **Environment Variables**: API tokens stored securely
3. **Error Handling**: Failed sends don't expose sensitive data
4. **Audit Trail**: All routing logged with request IDs
5. **Rate Limiting**: Health checks on 5-min intervals to avoid API overload

## Deployment

1. Import each JSON workflow into n8n
2. Configure credentials for each platform service
3. Set environment variables for database IDs and API tokens
4. Enable workflows one at a time for testing
5. Monitor logs and health checks before full production activation

## Testing

- Start with health-check workflow to verify all services are online
- Test each workflow individually before enabling response-router
- Use webhook test endpoints to validate message parsing
- Monitor Slack #myca-logs and #myca-alerts for runtime issues
