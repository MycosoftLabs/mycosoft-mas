# MYCA Implementation via Cursor Claude Code

## Quick Start for Morgan

You now have **two comprehensive documents** to implement the MYCA 17-phase plan using Cursor's Claude Code:

---

## Documents Overview

### 1. **CURSOR_CLI_QUICK_REFERENCE.md** (START HERE)
   - **Length:** ~310 lines
   - **Purpose:** Fast copy-paste commands for Claude Code
   - **Format:** Condensed prompts optimized for pasting
   - **Best for:** Quick reference while coding
   - **Content:**
     - One-liner prompts for each phase (2-13)
     - Deployment checklist (SSH commands)
     - Troubleshooting quick links
     - Credential locations
     - Implementation order

   **Use this file** when you need to generate code quickly. Just copy the prompt and paste into Cursor's Claude Code chat.

---

### 2. **CURSOR_CLI_COMMANDS.md** (COMPREHENSIVE REFERENCE)
   - **Length:** ~650 lines
   - **Purpose:** Detailed specifications for each component
   - **Format:** Full requirements, specifications, method signatures
   - **Best for:** Understanding the full architecture before building
   - **Content:**
     - Phase 1-17 detailed requirements
     - Complete API signatures for every class/method
     - Error handling specifications
     - Credential setup documentation
     - Full deployment procedures
     - File location mappings
     - Troubleshooting deep dives

   **Use this file** when you need details about what a component should do, error handling, logging, or when a Claude Code generation seems incomplete.

---

## Implementation Workflow

### For Each Phase:

1. **First Time:** Read the detailed section in `CURSOR_CLI_COMMANDS.md`
   - Understand the architecture
   - Know the dependencies
   - Understand error handling requirements

2. **Generation:** Use the condensed prompt from `CURSOR_CLI_QUICK_REFERENCE.md`
   - Copy the "Ask Claude Code:" prompt
   - Paste into Cursor's Claude Code interface
   - Wait for code generation

3. **Review & Adjust:** Cross-check against `CURSOR_CLI_COMMANDS.md`
   - Verify all required methods are implemented
   - Check error handling is included
   - Ensure logging statements are present
   - Validate credential paths match `/opt/myca/credentials/`

4. **Integration:** Use deployment checklist from quick reference
   - Test the component
   - Move to next phase

---

## Phase Implementation Sequence

**Recommended order (dependencies matter):**

```
Phase 1: VM Provisioning (Manual - Proxmox)
    ↓
Phase 2: Gateway Control Plane (Core routing)
    ↓
Phase 3: Node WebSocket Daemon (TypeScript)
    ↓
Phase 4: Exec/Browser Tools (Python wrappers)
    ↓
├─ Phase 5: MycoBrain Coordinator (MQTT)
├─ Phase 6: Google Workspace (Gmail/Drive)
├─ Phase 7-13: Integrations (Parallel OK)
│   ├─ Phase 7: Discord
│   ├─ Phase 8: Slack
│   ├─ Phase 9: Asana
│   ├─ Phase 10: Signal
│   ├─ Phase 11: WhatsApp
│   ├─ Phase 12: Gmail (via Phase 6)
│   └─ Phase 13: Notion
├─ Phase 14: Cowork/Cursor Headless (Optional)
├─ Phase 15: Health Monitoring (Optional)
├─ Phase 16: Response Router (n8n workflow)
└─ Phase 17: Security/Access Control (Final)
    ↓
FIX EXISTING CODE (3 critical modifications)
    ↓
DEPLOY TO MYCA-191 VM
    ↓
REGISTER WITH MAS ORCHESTRATOR
```

---

## Key Paths & Endpoints

### Codebase
```
/home/myca/mycosoft_mas/
├── gateway/
│   ├── control_plane.py
│   └── session_manager.py
├── sandbox/node-daemon/
│   └── src/
│       ├── index.ts
│       ├── websocket-client.ts
│       ├── exec-handler.ts
│       ├── browser-handler.ts
│       ├── fs-handler.ts
│       ├── pty-manager.ts
│       └── browser-controller.ts
├── tools/
│   ├── exec_tool.py
│   └── browser_tool.py
├── integrations/
│   ├── google_workspace_client.py
│   ├── discord_client.py
│   ├── slack_client.py
│   ├── asana_client.py
│   ├── signal_client.py
│   ├── whatsapp_client.py
│   └── notion_client.py
├── devices/
│   └── mycobrain_coordinator.py
├── core/
│   ├── myca_main.py (MODIFY)
│   └── routers/
│       └── sandbox_ws.py
├── llm/
│   └── tool_pipeline.py (FIX)
└── consciousness/
    └── deliberation.py (FIX)
```

### Credentials (Secure, chmod 600)
```
/opt/myca/credentials/
├── google/
│   └── service_account.json
├── discord/
│   └── bot_token
├── slack/
│   └── bot_token (JSON: {bot_token, app_token})
├── asana/
│   └── pat
└── notion/
    └── integration_token
```

### Logs
```
/opt/myca/logs/
├── gateway_router.log
├── tool_pipeline.log
├── exec_tool.log
├── browser_tool.log
├── google_workspace.log
├── discord_bot.log
├── slack_client.log
├── asana_client.log
├── signal_client.log
├── whatsapp_client.log
├── notion_client.log
├── mycobrain_coordinator.log
└── audit.log
```

### Network Endpoints
```
FastAPI (MYCA Core)    : 192.168.0.191:8000
n8n Workflows          : 192.168.0.191:3000
Node Daemon WebSocket  : 192.168.0.191:9000
Redis                  : 192.168.0.189:6379
MQTT Broker            : 192.168.0.189:1883
```

---

## Three Critical Code Fixes

After generating Phase 2-13 components, you **must** apply these fixes to existing code:

### Fix 1: mycosoft_mas/llm/tool_pipeline.py
- Import ExecTool and BrowserTool
- Register tools with GatewayControlPlane in __init__
- Route all tool calls through gateway.route_tool_call()
- Add WebSocket response handling

See detailed prompt in `CURSOR_CLI_QUICK_REFERENCE.md` under "Fix 1: tool_pipeline.py"

### Fix 2: mycosoft_mas/consciousness/deliberation.py
- Update _check_tool_use() to check GatewayControlPlane registration
- Call gateway.verify_session() and gateway.route_tool_call()
- Return enhanced result with requires_sandbox info

See detailed prompt in `CURSOR_CLI_QUICK_REFERENCE.md` under "Fix 2: deliberation.py"

### Fix 3: mycosoft_mas/core/myca_main.py
- Import sandbox_ws router from mycosoft_mas.core.routers
- Add app.include_router(sandbox_ws.router, prefix="/ws")
- Register health check endpoint at /health/sandbox

See detailed prompt in `CURSOR_CLI_QUICK_REFERENCE.md` under "Fix 3: myca_main.py"

---

## Deployment Steps (Once Coding Complete)

1. **SSH into 192.168.0.191**
   ```bash
   ssh myca@192.168.0.191
   ```

2. **Clone/Update Codebase**
   ```bash
   cd /home/myca/mycosoft_mas
   git pull  # or initial clone
   ```

3. **Build & Start Services**
   ```bash
   docker compose -f docker-compose.myca-vm.yml build
   docker compose -f docker-compose.myca-vm.yml up -d
   ```

4. **Import n8n Workflows**
   ```bash
   export N8N_API_KEY="your_api_key"
   curl -X POST http://192.168.0.191:3000/api/v1/workflows \
     -H "X-N8N-API-KEY: $N8N_API_KEY" \
     -d @Workflows/n8n/MYCA_HealthCheck.json
   ```

5. **Add Credentials**
   - See "Deployment Checklist → Step 6" in `CURSOR_CLI_QUICK_REFERENCE.md`
   - Copy API tokens to `/opt/myca/credentials/*/`
   - Set permissions to 600

6. **Configure Firewall**
   ```bash
   sudo ufw enable
   sudo ufw allow 22/tcp 3000/tcp 8000/tcp 9000/tcp
   ```

7. **Verify Health**
   ```bash
   curl http://192.168.0.191:8000/health
   curl -I http://192.168.0.191:3000/
   wscat -c ws://192.168.0.191:9000
   ```

8. **Register with Orchestrator**
   ```bash
   curl -X POST http://orchestrator-host:5000/api/register-agent \
     -d '{...}' # See quick reference for full JSON
   ```

---

## Document Cross-Reference

| Need | Document | Section |
|------|----------|---------|
| Quick command to paste | `CURSOR_CLI_QUICK_REFERENCE.md` | Phase 2-13 |
| Architecture details | `CURSOR_CLI_COMMANDS.md` | Phase Overview |
| API specifications | `CURSOR_CLI_COMMANDS.md` | Component Details |
| Deployment steps | `CURSOR_CLI_QUICK_REFERENCE.md` | Deployment Checklist |
| Error handling | `CURSOR_CLI_COMMANDS.md` | Error handling subsections |
| Credential setup | Both | Credential locations sections |
| Troubleshooting | `CURSOR_CLI_QUICK_REFERENCE.md` | Troubleshooting table |

---

## Pro Tips for Morgan

1. **Use both documents:**
   - Keep `CURSOR_CLI_QUICK_REFERENCE.md` open in one window
   - Keep `CURSOR_CLI_COMMANDS.md` open in another
   - Quick ref for copy-paste, full reference for validation

2. **Test as you go:**
   - After each phase, test the component before moving to next
   - Use the smoke test commands from deployment section
   - Don't wait until end to discover integration issues

3. **Credential management:**
   - Create `/opt/myca/credentials/` structure early
   - Generate all API tokens upfront (before deployment)
   - Store in secure location, copy to VM during deployment
   - Never commit credentials to git

4. **n8n workflows:**
   - Cowork has pre-generated these (in `Workflows/n8n/`)
   - Don't modify them; import as-is during deployment
   - They work alongside your generated Python/TypeScript code

5. **Testing locally:**
   - Generate code locally in Cursor
   - Commit to git with proper commit messages
   - Deploy via Docker to MYCA VM
   - Don't try to run all services locally (they need VLAN 50 isolation)

6. **Debugging WebSocket issues:**
   - Node daemon must connect to 192.168.0.191:9000
   - Test with: `wscat -c ws://192.168.0.191:9000`
   - Check logs: `docker logs myca-node-daemon -f`
   - Verify firewall: `sudo ufw status verbose`

---

## Document Usage Summary

**CURSOR_CLI_QUICK_REFERENCE.md:**
- 307 lines
- Optimized for copy-paste
- Use during active coding
- One-liner commands
- Quick troubleshooting table

**CURSOR_CLI_COMMANDS.md:**
- 652 lines
- Full specifications
- Reference for architecture
- Complete API signatures
- Detailed error handling

---

## Next Steps

1. Open `CURSOR_CLI_QUICK_REFERENCE.md`
2. Start with Phase 2: Gateway Control Plane
3. Copy the prompt from the "Phase 2: Gateway Control Plane" section
4. Paste into Cursor's Claude Code chat
5. Follow generated code with Phase 3, 4, etc. in order

**You're ready to build MYCA!**

---

**Document Generated:** 2026-03-03  
**For:** Morgan (MYCOSOFT team)  
**Integration:** Cursor with Claude Code  
**Status:** Ready for Implementation
