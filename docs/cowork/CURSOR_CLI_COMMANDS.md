# MYCA Implementation — Cursor CLI Commands
## Quick Reference for Morgan

**Document Version:** 1.0 | **Date:** 2026-03-03 | **Status:** Ready for Implementation  
**Target Environment:** mycosoft_mas project directory  
**Integration:** Claude Code in Cursor (via MAS orchestrator)

---

## Overview

This document provides copy-paste-ready Claude Code commands for implementing the MYCA 17-phase plan. Each command is formatted as a direct prompt you can paste into Cursor's Claude Code interface. Commands reference the mycosoft_mas project structure and assume you have the existing codebase loaded in the workspace.

---

## Phase 1: VM Provisioning (Proxmox)

**Note:** These commands run on the Proxmox host directly (not via Cursor). Execute via SSH to Proxmox management interface.

### Create MYCA VM (ID 191)

```bash
# SSH to Proxmox host first, then:
qm create 191 \
  --name "MYCA-191" \
  --machine q35 \
  --memory 32768 \
  --cores 8 \
  --sockets 1 \
  --cpu host \
  --bios ovmf \
  --efidisk0 local-lvm:32 \
  --scsi0 local-lvm:256 \
  --ide2 local:iso/ubuntu-22.04.5-live-server-amd64.iso,media=cdrom \
  --net0 virtio,bridge=vmbr0,tag=50,firewall=1

# Boot and run installer
qm start 191
qm terminal 191

# During Ubuntu installer, configure:
# - Hostname: MYCA-191
# - Network: Manual IPv4 at 192.168.0.191/24, gateway 192.168.0.1
# - Root disk: Full 256GB unencrypted (no LVM)
# - User: myca (password: generate from vault)
# - SSH server: install and enable
```

### Post-Installation Setup

```bash
# SSH into 192.168.0.191 as myca user
ssh myca@192.168.0.191

# System updates
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential python3-pip

# Docker installation
curl -fsSL https://get.docker.com -o get-docker.sh && sudo bash get-docker.sh
sudo apt install -y docker-compose-plugin
sudo usermod -aG docker myca

# Firewall (UFW) - configure later in Phase 17
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 3000/tcp  # n8n
sudo ufw allow 8000/tcp  # FastAPI
sudo ufw allow 5900/tcp  # VNC (if needed)
# Don't enable yet - Phase 17 will finalize rules
```

---

## Phase 2: Gateway Control Plane

**Location:** `mycosoft_mas/gateway/`

### Ask Claude Code: Create Gateway Module Structure

```
Create the gateway module structure for MYCA with the following files:

1. mycosoft_mas/gateway/__init__.py
   - Empty init file with module docstring

2. mycosoft_mas/gateway/control_plane.py
   This is the core routing engine. Implement GatewayControlPlane class with:
   
   Methods:
   - __init__(redis_host="192.168.0.189", redis_port=6379)
   - route_tool_call(tool_name: str, params: dict) -> dict
     * Check if tool_name is in built-in tools (exec, browser, file)
     * If yes: route to built-in handler
     * If MCP prefix (e.g., "mcp_x_*"): route to MCP sandbox
     * If custom: route to appropriate sandbox via WebSocket
     * Return {"tool": tool_name, "status": "routed", "handler": handler_type}
   
   - register_tool(name: str, handler: callable, requires_sandbox: bool = False)
     * Store tool metadata in Redis under key "tools:{name}"
     * Built-in tools: exec_tool, browser_tool, file_tool (requires_sandbox=True)
     * Return {"registered": True, "tool": name}
   
   - get_session(session_id: str) -> dict
     * Query Redis for session at key "session:{session_id}"
     * Return session object with tool_whitelist, user_id, created_at
     * If not found: create new session, store, return
   
   - revoke_session(session_id: str) -> dict
     * Delete session from Redis
     * Return {"revoked": True}
   
   Properties:
   - _built_in_tools: ["exec_tool", "browser_tool", "file_tool"]
   - _redis_client: Redis connection object
   - _tool_registry: dict of registered tools
   
   Error handling:
   - Catch RedisConnectionError and fall back to in-memory cache
   - Log all route decisions to gateway_router.log
   - Raise ToolNotFoundError if tool not registered

Include docstrings explaining the routing logic: built-in tools execute in process, 
sandbox tools route through WebSocket to node-daemon, MCP tools use existing MCP protocol.
```

---

## Phase 3: Node WebSocket Daemon (TypeScript)

**Location:** `mycosoft_mas/sandbox/node-daemon/`

### Ask Claude Code: Initialize Node Daemon Project

```
Create the TypeScript Node.js daemon scaffold:

1. Directory structure:
   mycosoft_mas/sandbox/node-daemon/
   ├── src/
   │   ├── index.ts
   │   ├── websocket-client.ts
   │   ├── exec-handler.ts
   │   ├── browser-handler.ts
   │   ├── fs-handler.ts
   │   ├── pty-manager.ts
   │   └── browser-controller.ts
   ├── package.json
   ├── tsconfig.json
   ├── Dockerfile
   └── .env.example

2. package.json (via npm init):
   Dependencies:
   - ws (v8.14.0) - WebSocket server
   - @types/ws (v8.5.0)
   - playwright (v1.40.0) - Browser automation via CDP
   - @types/node (v20.x)
   - node-pty (v0.10.1) - PTY for shell sessions
   - typescript (v5.x)
   - tsx (v4.x) - TypeScript runner
   - dotenv (v16.x)
   
   Dev dependencies:
   - @types/node-pty
   - ts-node-dev

3. tsconfig.json:
   - target: ES2020
   - module: commonjs
   - lib: ES2020
   - declaration: true
   - outDir: dist
   - sourceMap: true

4. .env.example:
   GATEWAY_HOST=192.168.0.191
   GATEWAY_PORT=9000
   NODE_ROLE=sandbox-executor
   REDIS_URL=redis://192.168.0.189:6379
   LOG_LEVEL=info
```

---

## Phase 4: Exec Tool + Browser Tool

**Location:** `mycosoft_mas/tools/`

### Ask Claude Code: Create Exec Tool

```
Create mycosoft_mas/tools/exec_tool.py:

ExecTool class (Python wrapper around node-daemon):
- __init__(node_ws_url: str = "ws://192.168.0.191:9000")
- run_command(command: str, cwd: str = None, timeout: int = 30) -> dict
  * Send to node-daemon via WebSocket
  * Await response with correlation ID
  * Return {"stdout": str, "stderr": str, "exit_code": int, "duration_ms": int}
  * Raise ExecTimeoutError if timeout exceeded
  * Raise ExecError with stderr details if exit_code != 0

- run_background(command: str, cwd: str = None) -> str
  * Returns process_id for monitoring
  * Does not wait for completion

- send_input(process_id: str, input: str) -> dict
  * Send stdin to running background process

- kill_process(process_id: str) -> dict

- Properties:
  * _connection_pool: maintains WebSocket connection
  * _pending_requests: dict of {correlation_id: asyncio.Future}

Error handling:
- Automatic reconnect if WebSocket closes
- Command queuing if not connected (retry loop)
- Logging of all commands to exec_tool.log

Include docstrings with examples.
```

---

## Phase 5: Edge Node (MycoBrain) Coordinator

**Location:** `mycosoft_mas/devices/`

### Ask Claude Code: Create MycoBrain Coordinator

```
Create mycosoft_mas/devices/mycobrain_coordinator.py:

MycoBrainCoordinator class (ESP32 device management):
- __init__(mqtt_broker: str = "192.168.0.189", mqtt_port: int = 1883)
- register_device(device_id: str, device_type: str, capabilities: list[str]) -> dict
  * device_id: unique ESP32 identifier
  * device_type: "sensor_node", "actuator_node", "relay_node"
  * capabilities: ["temperature", "humidity", "relay_control", etc.]
  * Subscribe to MQTT topic: "myca/device/{device_id}/status"
  * Return {"registered": True, "topic": str}

- publish_command(device_id: str, command: str, params: dict) -> dict
  * Publish to "myca/device/{device_id}/command"
  * Include command_id, timestamp, params
  * Wait for ACK with 10s timeout

- get_device_status(device_id: str) -> dict
  * Query last known state
  * Return {"device_id", "status", "last_update", "metrics": {}}

Error handling:
- MQTT connection failures -> retry with backoff
- Command timeout -> raise TimeoutError
- Unknown device -> raise DeviceNotFoundError

Include support for batching commands to multiple devices.
```

---

## Phase 6: Google Workspace Integration

**Location:** `mycosoft_mas/integrations/`

### Ask Claude Code: Create Google Workspace Client

```
Create mycosoft_mas/integrations/google_workspace_client.py:

GoogleWorkspaceClient class:
- __init__(service_account_json: str = "/opt/myca/credentials/google/service_account.json")
  * Load service account credentials
  * Initialize Gmail, Drive, Calendar APIs with service account impersonation
  * Impersonate: schedule@mycosoft.org

- Gmail operations:
  * send_email(to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> dict
    - Compose and send via Gmail API
    - Return {"message_id": str, "sent_time": datetime}
  
  * read_emails(folder: str = "INBOX", limit: int = 10) -> list[dict]
    - Fetch emails with subject, from, date, body snippet
    - Return list of email objects
  
  * read_email_body(message_id: str) -> str
    - Get full email body (handle MIME multipart)

- Drive operations:
  * upload_file(file_path: str, folder_id: str = None) -> dict
    - Return {"file_id": str, "name": str, "web_view_link": str}
  
  * download_file(file_id: str, output_path: str) -> dict
  
  * list_files(folder_id: str = None) -> list[dict]
    - Return file metadata

- Calendar operations:
  * create_event(title: str, start_time: datetime, end_time: datetime, 
                 attendees: list[str] = None) -> dict
    - Return {"event_id": str, "calendar_link": str}
  
  * list_events(days_ahead: int = 7) -> list[dict]
    - Fetch upcoming events
  
  * delete_event(event_id: str) -> dict

Error handling:
- Google API rate limiting -> retry with exponential backoff
- Invalid credentials -> raise AuthenticationError
- Log all operations to google_workspace.log

Include docstrings with Gmail/Drive/Calendar API v1 references.
```

---

## Phase 7: Discord Integration

**Location:** `mycosoft_mas/integrations/discord_client.py`

### Ask Claude Code: Create Discord Bot Client

```
Create mycosoft_mas/integrations/discord_client.py:

DiscordBotClient class:
- __init__(token_path: str = "/opt/myca/credentials/discord/bot_token")
  * Load bot token from file
  * Initialize discord.py Client
  * Register event handlers: on_ready, on_message

- send_message(channel_id: int, content: str, embed: dict = None) -> dict
  * Post message to channel
  * Support Discord embeds for rich formatting
  * Return {"message_id": int, "timestamp": datetime}

- send_dm(user_id: int, content: str) -> dict
  * Send direct message
  * Return message metadata

- listen_for_messages(guild_id: int = None) -> callback
  * Register handler for incoming messages
  * Filter by guild if specified
  * Parse command prefix: "!myca <command> <args>"

- create_slash_command(name: str, description: str, options: list = None) -> dict
  * Register slash command
  * Return {"command_id": int}

Error handling:
- Discord connection errors -> auto-reconnect with backoff
- Invalid channel -> raise ChannelNotFoundError
- Rate limiting -> respect Discord API rate limits
- Log to discord_bot.log

Credentials file format:
/opt/myca/credentials/discord/bot_token
(single line: "YOUR_DISCORD_BOT_TOKEN")
```

---

## Phase 8: Slack Integration

**Location:** `mycosoft_mas/integrations/slack_client.py`

### Ask Claude Code: Create Slack App Client

```
Create mycosoft_mas/integrations/slack_client.py:

SlackAppClient class:
- __init__(token_path: str = "/opt/myca/credentials/slack/bot_token")
  * Load OAuth bot token from file
  * Initialize slack_sdk.WebClient

- send_message(channel: str, text: str, blocks: list = None) -> dict
  * Post message to channel (supports Block Kit)
  * Return {"ts": str, "channel": str}

- send_dm(user_id: str, text: str) -> dict
  * Open DM channel and send message

- listen_for_messages(callback: callable)
  * Register handler for message events (via Socket Mode)
  * Respond to mentions and direct messages

- list_channels() -> list[dict]
  * Return public channels

- get_user_info(user_id: str) -> dict
  * Return user profile (name, email, avatar, etc.)

Error handling:
- Slack API errors -> raise SlackAPIError
- Invalid channel -> raise ChannelNotFoundError
- Token expiration -> auto-refresh via refresh_token
- Log to slack_client.log

Required OAuth scopes:
- chat:write
- chat:write.public
- users:read
- users:read.email

Credentials file format:
/opt/myca/credentials/slack/bot_token
(JSON: {"bot_token": "xoxb-...", "app_token": "xapp-..."})
```

---

## Phase 9: Asana Integration

**Location:** `mycosoft_mas/integrations/asana_client.py`

### Ask Claude Code: Create Asana Client

```
Create mycosoft_mas/integrations/asana_client.py:

AsanaClient class:
- __init__(pat_path: str = "/opt/myca/credentials/asana/pat")
  * Load Personal Access Token from file
  * Initialize asana.Client with auth header

- create_task(workspace_id: str, name: str, description: str = None, 
              assignee_id: str = None, due_date: str = None) -> dict
  * Create new task
  * Return {"task_id": str, "url": str}

- list_tasks(project_id: str, completed: bool = False) -> list[dict]
  * Fetch tasks in project
  * Return task objects with id, name, assignee, due_date, status

- update_task(task_id: str, **kwargs) -> dict
  * Update task fields (name, description, assignee, due_date, status)
  * Return updated task

- get_project_sections(project_id: str) -> list[dict]
  * List sections/columns in a project

- move_task(task_id: str, section_id: str) -> dict
  * Move task to different section

Error handling:
- Invalid resource IDs -> raise NotFoundError
- Authentication issues -> raise AuthenticationError
- Log to asana_client.log

Credentials file format:
/opt/myca/credentials/asana/pat
(single line: "ASANA_PAT_TOKEN_VALUE")
```

---

## Phase 10: Signal Integration

**Location:** `mycosoft_mas/integrations/signal_client.py`

### Ask Claude Code: Create Signal Client (signal-cli)

```
Create mycosoft_mas/integrations/signal_client.py:

SignalClient class (wrapper around signal-cli):
- __init__(phone_number: str = "+1-[MYCA-PHONE]", signal_cli_path: str = "/opt/signal-cli/bin/signal-cli")
  * Phone number registered for schedule@mycosoft.org
  * Use ExecTool to call signal-cli binary

- send_message(recipient: str, message: str, attachments: list[str] = None) -> dict
  * Construct signal-cli send command
  * Execute via ExecTool
  * Return {"recipient": str, "sent": True, "timestamp": datetime}

- receive_messages(callback: callable)
  * Monitor signal-cli daemon for incoming messages
  * Parse and dispatch to callback handler

Error handling:
- signal-cli daemon not running -> auto-start
- Network errors -> retry logic
- Invalid phone format -> raise ValidationError
- Log to signal_client.log

Note: Requires separate registration step (Phase 10 setup).
Signal account tied to phone number, not email.
```

---

## Phase 11: WhatsApp Integration

**Location:** `mycosoft_mas/integrations/whatsapp_client.py`

### Ask Claude Code: Create WhatsApp Client (Baileys)

```
Create mycosoft_mas/integrations/whatsapp_client.py:

WhatsAppClient class (Python interface to Baileys node daemon):
- __init__(node_ws_url: str = "ws://192.168.0.191:9000")
  * Connect to node-daemon (same WebSocket as browser)
  * Request "whatsapp_handler" capability

- pair_device() -> dict
  * Generate QR code via Baileys
  * Return {"qr_code": base64_image, "expires_in": 30}
  * Device links via camera scan (WhatsApp Web)

- send_message(phone_number: str, message: str, media: dict = None) -> dict
  * Send text or media message
  * Return {"message_id": str, "sent_time": datetime}

- receive_messages(callback: callable)
  * Listen for incoming WhatsApp messages
  * Parse sender, message, timestamp
  * Dispatch to callback

Error handling:
- QR code expired -> auto-regenerate
- Session lost -> re-pair required
- Invalid phone format -> raise ValidationError
- Log to whatsapp_client.log

Session storage: ~/.myca/whatsapp_sessions/ (encrypted)
```

---

## Phase 13: Notion Integration

**Location:** `mycosoft_mas/integrations/notion_client.py`

### Ask Claude Code: Create Notion Client

```
Create mycosoft_mas/integrations/notion_client.py:

NotionClient class:
- __init__(token_path: str = "/opt/myca/credentials/notion/integration_token")
  * Load Notion integration token
  * Initialize notion-client

- query_database(database_id: str, filter: dict = None, sorts: list = None) -> list[dict]
  * Query Notion database with filters
  * Return list of page objects with properties

- create_page(database_id: str, properties: dict, content: str = None) -> dict
  * Create new database entry
  * Support rich text content blocks
  * Return {"page_id": str, "url": str}

- update_page(page_id: str, properties: dict) -> dict
  * Update page properties

Error handling:
- Invalid token -> raise AuthenticationError
- Database not shared -> raise PermissionError
- Rate limiting -> implement backoff
- Log to notion_client.log

Credentials file format:
/opt/myca/credentials/notion/integration_token
(single line: "secret_XXXXXXXXXXXXX")
```

---

## Existing Files to Modify

### 1. Fix tool_pipeline.py

Ask Claude Code:

```
Modify mycosoft_mas/llm/tool_pipeline.py:

Current state: code_execute tool is broken, not properly integrated with GatewayControlPlane.

Changes needed:
1. Import ExecTool and BrowserTool from mycosoft_mas.tools
2. In ToolPipeline.__init__(), register tools:
   - self.gateway.register_tool("exec_tool", ExecTool.run_command, requires_sandbox=True)
   - self.gateway.register_tool("browser_tool", BrowserTool.navigate, requires_sandbox=True)
   - self.gateway.register_tool("file_tool", built_in_file_handler, requires_sandbox=False)

3. Update route_tool_call() method:
   - Call self.gateway.route_tool_call(tool_name, params) instead of direct execution
   - Await WebSocket response from node-daemon for sandbox tools
   - Return response with same format as before for backward compatibility

4. Add error handling:
   - Catch WebSocket timeouts and raise ToolExecutionError
   - Log all tool routing decisions
   - Add retry logic for transient failures (3 retries max)

5. Document the routing behavior in docstrings:
   - exec_tool and browser_tool route to node-daemon (sandbox)
   - file_tool routes to built-in handler (no sandbox needed for workspace files)
   - All routing decisions logged to tool_pipeline.log

This fix enables safe tool execution by enforcing sandbox=True for code execution.
```

---

## Deployment Overview

Full deployment sequence for the MYCA VM:

1. SSH into 192.168.0.191
2. Clone repo / copy configs
3. docker compose -f docker-compose.myca-vm.yml up -d
4. Import n8n workflows
5. Verify health endpoints
6. Register with MAS orchestrator

---

## File Locations Reference

| Component | Path | Type |
|-----------|------|------|
| Codebase | `/home/myca/mycosoft_mas/` | Git repository |
| Credentials (secure) | `/opt/myca/credentials/` | Credential files (chmod 600) |
| Logs | `/opt/myca/logs/` | Log files |
| Docker Compose | `/home/myca/mycosoft_mas/docker-compose.myca-vm.yml` | Config file |
| n8n Workflows | `Workflows/n8n/` | JSON files |
| Gateway logs | `mycosoft_mas/logs/gateway_router.log` | Debug logs |
| Tool execution logs | `mycosoft_mas/logs/tool_pipeline.log` | Tool routing logs |
| Node daemon logs | Docker container stdout | Container logs |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-03 | Initial comprehensive command sheet |

---

**End of MYCA Implementation Command Sheet**

For questions, refer to the mycosoft_mas README or contact the MYCOSOFT development team.
