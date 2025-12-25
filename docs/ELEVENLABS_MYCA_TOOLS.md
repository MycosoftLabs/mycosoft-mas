# MYCA ElevenLabs Agent Tools Configuration

This document defines the tool schemas for the MYCA ElevenLabs conversational AI agent to integrate with n8n and the Mycosoft MAS.

## Agent Configuration

**Agent ID**: `agent_2901kcpp3bk2fcjshrajb9fxvv3y`
**Voice**: Arabella (`aEO01A4wXwd1O8GPgGlF`)
**Model**: `eleven_turbo_v2`

## Tool Definitions

### 1. `myca_chat` - Direct Chat with MYCA Orchestrator

Send a message directly to the MYCA orchestrator for processing.

**Endpoint**: `POST http://localhost:8001/voice/orchestrator/chat`

**Request Schema**:
```json
{
  "message": "string (required) - The user's message or command",
  "conversation_id": "string (optional) - Session ID for conversation continuity",
  "want_audio": false
}
```

**Response Schema**:
```json
{
  "conversation_id": "string",
  "response_text": "string - MYCA's response"
}
```

**When to Use**: For general questions, status queries, and commands that MYCA handles directly.

---

### 2. `agent_registry_list` - List All Available Agents

Get a list of all agents registered in the MAS.

**Endpoint**: `GET http://localhost:8001/agents/registry/`

**Response Schema**:
```json
{
  "agents": [
    {
      "agent_id": "string",
      "name": "string",
      "display_name": "string",
      "description": "string",
      "category": "string",
      "capabilities": ["string"],
      "is_active": boolean
    }
  ],
  "total_agents": number,
  "active_agents": number
}
```

**When to Use**: When user asks "what agents are available?" or "list all agents".

---

### 3. `agent_registry_search` - Search Agents by Keyword

Search for agents matching a keyword.

**Endpoint**: `GET http://localhost:8001/agents/registry/search?q={keyword}`

**Response Schema**:
```json
{
  "query": "string",
  "results": [
    {
      "agent_id": "string",
      "display_name": "string",
      "description": "string",
      "category": "string"
    }
  ],
  "count": number
}
```

**When to Use**: When user asks about specific agent capabilities.

---

### 4. `agent_route_voice` - Route Voice Command to Agent

Route a voice transcript to the appropriate agent.

**Endpoint**: `POST http://localhost:8001/agents/registry/route/voice`

**Request Schema**:
```json
{
  "transcript": "string (required) - The voice transcript to route",
  "actor": "string - Who is speaking (default: morgan)",
  "session_id": "string (optional)"
}
```

**Response Schema**:
```json
{
  "matched_agents": [
    {
      "agent_id": "string",
      "display_name": "string",
      "category": "string",
      "is_active": boolean,
      "requires_confirmation": boolean
    }
  ],
  "primary_agent": {
    "agent_id": "string",
    "name": "string",
    "display_name": "string",
    "description": "string",
    "requires_confirmation": boolean
  },
  "requires_confirmation": boolean,
  "routing_prompt": "string"
}
```

**When to Use**: For complex commands that should be routed to specialized agents.

---

### 5. `n8n_command` - Execute n8n Workflow Command

Send a command through the n8n workflow system.

**Endpoint**: `POST http://localhost:5678/webhook/myca/command`

**Request Schema**:
```json
{
  "request_id": "string (optional)",
  "actor": "string - Who is executing (default: morgan)",
  "intent": "string - command, query, status",
  "action": "string - The action to perform",
  "params": {},
  "confirm": boolean
}
```

**Response Schema**:
```json
{
  "ok": boolean,
  "request_id": "string",
  "result": {}
}
```

**When to Use**: For infrastructure commands (Proxmox, UniFi, NAS).

---

### 6. `speech_turn` - Process Speech Turn

Process a speech turn for wake-word detection and intent parsing.

**Endpoint**: `POST http://localhost:5678/webhook/myca/speech_turn`

**Request Schema**:
```json
{
  "request_id": "string (optional)",
  "actor": "string",
  "transcript": "string - The spoken text"
}
```

**Response Schema**:
```json
{
  "ok": boolean,
  "request_id": "string",
  "intent": "string - command, status, confirm, abort",
  "next": "string - Next endpoint to call",
  "message": "string"
}
```

**When to Use**: On every voice turn for intent classification.

---

### 7. `speech_safety` - Safety Check for Commands

Store pending action and get confirmation challenge for risky commands.

**Endpoint**: `POST http://localhost:5678/webhook/myca/speech_safety`

**Request Schema**:
```json
{
  "request_id": "string",
  "actor": "string",
  "transcript": "string"
}
```

**Response Schema**:
```json
{
  "ok": boolean,
  "request_id": "string",
  "risk_level": "string - read, write, destructive",
  "pending": boolean,
  "confirmation_required": boolean,
  "prompt": "string - Challenge phrase to speak",
  "next": "string - Next endpoint"
}
```

**When to Use**: Before executing write or destructive actions.

---

### 8. `speech_confirm` - Confirm Risky Action

Validate confirmation phrase and execute pending action.

**Endpoint**: `POST http://localhost:5678/webhook/myca/speech_confirm`

**Request Schema**:
```json
{
  "request_id": "string",
  "actor": "string",
  "transcript": "string - The confirmation phrase"
}
```

**Response Schema**:
```json
{
  "ok": boolean,
  "request_id": "string",
  "status": "string - confirmed, aborted, forwarded",
  "myca_response": {}
}
```

**Confirmation Phrases**:
- For write actions: "Confirm and proceed"
- For destructive actions: "Confirm irreversible action"
- To abort: "Abort" or "Cancel that"

---

### 9. `infrastructure_proxmox` - Proxmox Operations

Execute Proxmox infrastructure commands.

**Endpoint**: `POST http://localhost:8001/api/proxmox/{action}`

**Actions**:
- `GET /api/proxmox/nodes` - List all nodes
- `GET /api/proxmox/vms` - List all VMs
- `POST /api/proxmox/snapshot` - Create VM snapshot
- `POST /api/proxmox/reboot` - Reboot VM

**When to Use**: For Proxmox-related commands.

---

### 10. `infrastructure_unifi` - UniFi Network Operations

Execute UniFi network commands.

**Endpoint**: `POST http://localhost:8001/api/unifi/{action}`

**Actions**:
- `GET /api/unifi/topology` - Get network topology
- `GET /api/unifi/clients` - List connected clients
- `GET /api/unifi/vlans` - List VLANs

**When to Use**: For network-related queries.

---

## Recommended Tool Call Sequence

### Standard Query Flow
1. User speaks → STT
2. Call `speech_turn` to classify intent
3. If `intent == "command"`:
   - Call `agent_route_voice` to find agent
   - If `requires_confirmation`: Call `speech_safety`
   - Speak confirmation prompt
   - Wait for confirmation → Call `speech_confirm`
4. If `intent == "query"`:
   - Call `myca_chat` directly
5. Speak response

### Infrastructure Command Flow
1. User: "Snapshot DC1"
2. Call `speech_turn` → `intent: command`
3. Call `speech_safety` → `risk_level: write`
4. Speak: "That action affects live infrastructure. Please confirm."
5. User: "Confirm and proceed"
6. Call `speech_confirm` → Executes via `n8n_command`
7. Speak result

---

## ElevenLabs Agent System Prompt Addition

Add this to your ElevenLabs agent system prompt:

```
TOOL USAGE:
- Use `myca_chat` for general questions and status queries
- Use `agent_route_voice` when user asks for specific agent capabilities
- Use `n8n_command` for infrastructure operations (always with confirm=false first)
- Use `speech_safety` before any write or destructive operation
- Always speak the confirmation prompt and wait for user confirmation

INFRASTRUCTURE COMMANDS (require confirmation):
- Proxmox: snapshot, reboot, start, stop VMs
- UniFi: VLAN changes, client blocking
- NAS: backup operations

CONFIRMATION WORKFLOW:
1. Detect infrastructure command
2. Call speech_safety to get challenge
3. Speak: "That action affects [target]. Say 'Confirm and proceed' to continue."
4. Wait for user confirmation
5. Call speech_confirm with user's response
6. Report result
```

---

## API Base URLs

| Service | URL |
|---------|-----|
| MAS Orchestrator | `http://localhost:8001` |
| n8n Webhooks | `http://localhost:5678/webhook` |
| ElevenLabs TTS Proxy | `http://localhost:5501` |

---

## Testing Tools

Test each tool with curl:

```bash
# Test myca_chat
curl -X POST http://localhost:8001/voice/orchestrator/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What agents are available?"}'

# Test agent registry
curl http://localhost:8001/agents/registry/

# Test voice routing
curl -X POST http://localhost:8001/agents/registry/route/voice \
  -H "Content-Type: application/json" \
  -d '{"transcript": "check the financial status"}'

# Test n8n command
curl -X POST http://localhost:5678/webhook/myca/command \
  -H "Content-Type: application/json" \
  -d '{"actor": "morgan", "intent": "status", "action": "system_health"}'
```



