# MYCA Cursor CLI — Quick Command Reference

**TL;DR for Morgan: Copy → Paste into Cursor → Claude Code generates code**

---

## Phase 2: Gateway Control Plane (Start Here)

```
Ask Claude Code: Create gateway/control_plane.py implementing GatewayControlPlane 
class with route_tool_call(tool_name, params), register_tool(), get_session(), 
revoke_session(). Connect to Redis at 192.168.0.189:6379. Route built-in tools 
(exec, browser, file) vs MCP tools differently. All routing logged to gateway_router.log
```

---

## Phase 3: Node WebSocket Daemon (TypeScript)

```
Ask Claude Code: Initialize Node.js/TypeScript project in mycosoft_mas/sandbox/node-daemon/
Install: ws, playwright, node-pty, typescript. Generate src/index.ts, src/websocket-client.ts 
(connects to 192.168.0.191:9000 with handshake role="node-daemon"), src/exec-handler.ts, 
src/browser-handler.ts, src/fs-handler.ts, src/pty-manager.ts, src/browser-controller.ts (Playwright CDP)
```

---

## Phase 4: Exec + Browser Tools (Python)

```
Ask Claude Code: Create mycosoft_mas/tools/exec_tool.py - ExecTool class that 
sends commands to node-daemon via WebSocket (ws://192.168.0.191:9000), 
returns {stdout, stderr, exit_code, duration_ms}. Include run_command(), 
run_background(), send_input(), kill_process() with auto-reconnect
```

```
Ask Claude Code: Create mycosoft_mas/tools/browser_tool.py - BrowserTool class 
wrapping node-daemon browser handler. Implement navigate(), click(), type(), 
screenshot(), get_content(), wait_for_selector(), evaluate(). WebSocket to same endpoint.
```

---

## Phase 6: Google Workspace (Gmail, Drive, Calendar)

```
Ask Claude Code: Create mycosoft_mas/integrations/google_workspace_client.py 
using google-auth and google-api-client. Load service account from 
/opt/myca/credentials/google/service_account.json, impersonate 
schedule@mycosoft.org. Implement: send_email(), read_emails(), read_email_body(), 
upload_file(), download_file(), list_files(), create_event(), list_events(), 
delete_event(). Log to google_workspace.log with rate limit handling.
```

---

## Phase 7-11: Platform Integrations (One Command Each)

### Phase 7: Discord

```
Ask Claude Code: Create mycosoft_mas/integrations/discord_client.py - DiscordBotClient 
class. Load token from /opt/myca/credentials/discord/bot_token. Implement: send_message(), 
send_dm(), listen_for_messages(), create_slash_command(). Handle reconnection, 
rate limits, invalid channels. Log to discord_bot.log
```

### Phase 8: Slack

```
Ask Claude Code: Create mycosoft_mas/integrations/slack_client.py - SlackAppClient 
class using slack_sdk. Load token from /opt/myca/credentials/slack/bot_token (JSON format: 
{"bot_token": "xoxb-...", "app_token": "xapp-..."}). Implement: send_message(), send_dm(), 
listen_for_messages(), list_channels(), get_user_info(). Log to slack_client.log
```

### Phase 9: Asana

```
Ask Claude Code: Create mycosoft_mas/integrations/asana_client.py - AsanaClient class. 
Load PAT from /opt/myca/credentials/asana/pat. Implement: create_task(), list_tasks(), 
update_task(), get_project_sections(), move_task(), add_task_comment(). 
Set up webhook receiver. Log to asana_client.log
```

### Phase 10: Signal

```
Ask Claude Code: Create mycosoft_mas/integrations/signal_client.py - SignalClient class 
using signal-cli (/opt/signal-cli/bin/signal-cli). Implement: send_message(), 
receive_messages(callback). Monitor signal-cli daemon for incoming. 
Account tied to phone number +1-[MYCA-PHONE]. Log to signal_client.log
```

### Phase 11: WhatsApp (Baileys)

```
Ask Claude Code: Create mycosoft_mas/integrations/whatsapp_client.py - WhatsAppClient 
class connecting to node-daemon (ws://192.168.0.191:9000). Implement: pair_device() 
returns QR code, send_message(), receive_messages(callback). Session state at 
~/.myca/whatsapp_sessions/. Log to whatsapp_client.log
```

---

## Phase 13: Notion

```
Ask Claude Code: Create mycosoft_mas/integrations/notion_client.py - NotionClient class. 
Load token from /opt/myca/credentials/notion/integration_token. Implement: 
query_database(), create_page(), update_page(), append_to_page(), search_pages(), 
get_page_content(). Log to notion_client.log
```

---

## Phase 5: MycoBrain Coordinator (ESP32 Devices)

```
Ask Claude Code: Create mycosoft_mas/devices/mycobrain_coordinator.py - 
MycoBrainCoordinator class using MQTT. Broker at 192.168.0.189:1883. 
Implement: register_device(), publish_command(), get_device_status(), 
listen_for_events(). Topic pattern: myca/device/{device_id}/command. 
Support batching. Log to mycobrain_coordinator.log
```

---

## Fix Existing Code (3 Critical Pieces)

### Fix 1: tool_pipeline.py

```
Ask Claude Code: Modify mycosoft_mas/llm/tool_pipeline.py - Import ExecTool and 
BrowserTool. In __init__ register all tools via GatewayControlPlane with requires_sandbox flags. 
Update route_tool_call() to call self.gateway.route_tool_call(). Add WebSocket 
response handling for sandbox tools. Log all routing decisions.
```

### Fix 2: deliberation.py

```
Ask Claude Code: Modify mycosoft_mas/consciousness/deliberation.py - Update 
_check_tool_use() method to call self.gateway.verify_session() and 
self.gateway.route_tool_call(). Return enhanced result with {tool, valid, handler, 
requires_sandbox}. Check both MINDEX and GatewayControlPlane registration. 
Log validation decisions.
```

### Fix 3: myca_main.py

```
Ask Claude Code: Modify mycosoft_mas/core/myca_main.py - Import 
sandbox_ws from mycosoft_mas.core.routers. Add app.include_router(sandbox_ws.router, 
prefix="/ws", tags=["sandbox"]). Add startup event logging "Sandbox WebSocket 
endpoint ready at ws://0.0.0.0:8000/ws/sandbox/{session_id}". Add GET /health/sandbox endpoint.
```

---

## Deployment Checklist (SSH Commands)

### 1. Provision VM (SSH to Proxmox host)
```bash
# Run qm create 191 with specs: 8 vCPU, 32GB RAM, 256GB SSD, VLAN 50, IP 192.168.0.191
# Boot Ubuntu 22.04 installer and complete setup as root/myca user
```

### 2. Post-Install (SSH 192.168.0.191)
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin python3-pip
sudo usermod -aG docker myca
newgrp docker
```

### 3. Clone & Setup
```bash
cd /home/myca && git clone https://github.com/MYCOSOFT/mycosoft_mas.git
cd mycosoft_mas
mkdir -p /opt/myca/credentials/{google,discord,slack,asana,notion}
mkdir -p /opt/myca/logs
sudo chown -R myca:myca /opt/myca
```

### 4. Deploy Services
```bash
docker compose -f docker-compose.myca-vm.yml build
docker compose -f docker-compose.myca-vm.yml up -d
# Verify: docker compose -f docker-compose.myca-vm.yml ps
```

### 5. Import n8n Workflows
```bash
# Get API key from http://192.168.0.191:3000
export N8N_API_KEY="your_key"
curl -X POST http://192.168.0.191:3000/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @Workflows/n8n/MYCA_HealthCheck.json
```

### 6. Add Credentials
```bash
# Discord token
echo "BOT_TOKEN" | sudo tee /opt/myca/credentials/discord/bot_token
sudo chmod 600 /opt/myca/credentials/discord/bot_token

# Slack (JSON)
echo '{"bot_token":"xoxb-...","app_token":"xapp-..."}' | sudo tee /opt/myca/credentials/slack/bot_token
sudo chmod 600 /opt/myca/credentials/slack/bot_token

# Asana PAT
echo "PAT_VALUE" | sudo tee /opt/myca/credentials/asana/pat
sudo chmod 600 /opt/myca/credentials/asana/pat

# Google service account JSON (download + copy)
sudo cp ~/service_account.json /opt/myca/credentials/google/
sudo chmod 600 /opt/myca/credentials/google/service_account.json

# Notion
echo "secret_TOKEN" | sudo tee /opt/myca/credentials/notion/integration_token
sudo chmod 600 /opt/myca/credentials/notion/integration_token
```

### 7. Configure Firewall
```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow 22/tcp 3000/tcp 8000/tcp 9000/tcp
sudo ufw allow from 192.168.0.0/24 to any port 6379
sudo ufw allow from 192.168.0.0/24 to any port 1883
```

### 8. Verify Endpoints
```bash
# Health check
curl http://192.168.0.191:8000/health

# n8n UI
curl -I http://192.168.0.191:3000/

# WebSocket test
wscat -c ws://192.168.0.191:9000
```

### 9. Register with Orchestrator
```bash
curl -X POST http://orchestrator-host:5000/api/register-agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "MYCA-191",
    "api_url": "http://192.168.0.191:8000",
    "websocket_url": "ws://192.168.0.191:9000",
    "capabilities": ["tool_routing", "sandbox_execution", "integration_hub"]
  }'
```

---

## Troubleshooting Quick Links

| Issue | Command |
|-------|---------|
| Node daemon not connecting | `docker logs myca-node-daemon -f` |
| Tool routing fails | `tail -f /home/myca/mycosoft_mas/logs/gateway_router.log` |
| Redis unreachable | `redis-cli -h 192.168.0.189 ping` |
| n8n workflow import fails | `curl -H "X-N8N-API-KEY: $N8N_API_KEY" http://192.168.0.191:3000/api/v1/workflows` |
| Firewall blocks traffic | `sudo ufw status verbose` (temporarily: `sudo ufw disable`) |
| WebSocket connection fails | `wscat -c ws://192.168.0.191:9000` |

---

## Key Endpoints

- **FastAPI Core:** http://192.168.0.191:8000
- **n8n Workflows:** http://192.168.0.191:3000
- **Node Daemon WebSocket:** ws://192.168.0.191:9000
- **Redis:** redis://192.168.0.189:6379
- **MQTT Broker:** mqtt://192.168.0.189:1883

---

## Credential Locations (Secured)

- Discord: `/opt/myca/credentials/discord/bot_token`
- Slack: `/opt/myca/credentials/slack/bot_token` (JSON)
- Asana: `/opt/myca/credentials/asana/pat`
- Google: `/opt/myca/credentials/google/service_account.json`
- Notion: `/opt/myca/credentials/notion/integration_token`
- Signal: Phone number in config (account tied to number, not file)

---

## Implementation Order (Sequential)

1. Phase 1: VM Provisioning → Phase 2: Gateway
2. Phase 3: Node Daemon → Phase 4: Exec/Browser Tools
3. Phase 5: MycoBrain → Phase 6: Google Workspace
4. Phase 7-13: Platform Integrations (parallel OK)
5. Fix Existing Code (Phase 4+)
6. Deploy & Test
7. Register with Orchestrator

---

**Document Version:** 1.0 | **Last Updated:** 2026-03-03
