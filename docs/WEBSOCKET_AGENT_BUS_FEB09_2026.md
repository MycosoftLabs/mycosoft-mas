# WebSocket Agent Bus - February 9, 2026

## Overview

The WebSocket Agent Bus provides real-time agent-to-agent messaging over persistent WebSocket connections. It extends the existing MAS real-time infrastructure (Redis pub/sub, WebSocketHub) without replacing it.

## Architecture

```
                    EXISTING (KEPT)                         NEW (ADDED)

   +-----------------+     +-----------------+      +------------------------+
   | Redis Pub/Sub   |     | WebSocketHub    |      | Agent Event Bus        |
   | (6 channels)    |<--->| (pubsub.py)     |<---->| /ws/agent-bus         |
   | - devices:telem |     | - connections   |      | - agent sessions       |
   | - agents:status |     | - subscriptions |      | - task routing         |
   | - experiments   |     | - broadcasts    |      | - heartbeats           |
   | - crep:live     |     +-----------------+      | - tool calls           |
   | - agents:tasks  |                              +------------------------+
   | - agents:tool_calls|                                  |
   +-----------------+                                     v
           |                                       +------------------------+
           v                                       | Agent WS Clients       |
   +-----------------+                             | - BaseAgent extension  |
   | A2A HTTP API    |                             | - Reconnect logic      |
   | (a2a_api.py)    |                             | - Local buffering      |
   | - /a2a/v1/*     |                             +------------------------+
   +-----------------+
   +-----------------+
   | A2A WebSocket   |
   | /a2a/v1/ws      |
   +-----------------+
```

## Endpoints

| Endpoint | Transport | Description |
|----------|-----------|-------------|
| `/ws/agent-bus` | WebSocket | Agent Event Bus – persistent connection for agents |
| `/a2a/v1/ws` | WebSocket | A2A protocol with streaming responses |

## Feature Flags

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `MYCA_AGENT_BUS_ENABLED` | false | Enable /ws/agent-bus WebSocket endpoint |
| `MYCA_AGENT_WS_ENABLED` | false | Enable BaseAgent WebSocket mixin (agents connect to bus) |
| `MYCA_A2A_WS_ENABLED` | false | Enable /a2a/v1/ws WebSocket endpoint |
| `MYCA_POLICY_ENGINE_ENABLED` | false | Validate events through policy engine before publish |

## Redis Channels

| Channel | Purpose |
|---------|---------|
| `agents:tasks` | Task delegation and routing |
| `agents:tool_calls` | Tool execution events, MCP progress |

## Event Schema

```python
class AgentEvent(BaseModel):
    type: Literal["task", "result", "alert", "heartbeat", "tool_call", "status"]
    from_agent: str
    to_agent: str | Literal["broadcast"]
    payload: Dict[str, Any]
    timestamp: datetime
    trace_id: str
    classification: str  # UNCLASS, CUI, ITAR
```

## Agent WebSocket Protocol

1. Connect to `ws://{MAS_HOST}:8001/ws/agent-bus`
2. Send initial JSON: `{"agent_id": "my-agent", "channels": ["agents:status", "agents:tasks", "agents:tool_calls"]}`
3. Receive `{"type": "connected", "payload": {...}}`
4. Send events: `{"type": "heartbeat", "to_agent": "broadcast", "payload": {}}`
5. Receive messages: `{"type": "message", "data": {...}}`

## BaseAgent Integration

Agents can optionally connect to the bus via `AgentWebSocketMixin`:

- Set `config["ws_enabled"] = True` and `MYCA_AGENT_WS_ENABLED=true`
- Mixin provides `connect_to_bus()`, `disconnect_from_bus()`, `send_event()`, `receive_events()`
- Exponential backoff on reconnect: 1s, 2s, 4s, 8s, 16s, max 30s
- Events buffered when disconnected

## MCP Progress Notifications

MCP servers (task_management_server, mcp_memory_server) emit progress to `agents:tool_calls` for long-running operations:

- `gap_scan`, `submit_coding_task`, `memory_search`
- Progress payload: `{"type": "progress", "tool": "...", "progress": N, "total": M, "message": "..."}`

## Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/realtime/event_schema.py` | AgentEvent model |
| `mycosoft_mas/realtime/agent_bus.py` | WebSocket server router |
| `mycosoft_mas/realtime/agent_session.py` | Session tracking, heartbeats |
| `mycosoft_mas/agents/websocket_mixin.py` | AgentWebSocketMixin |
| `mycosoft_mas/core/routers/a2a_websocket.py` | A2A WebSocket endpoint |
| `mycosoft_mas/security/policy_engine.py` | Event validation |
| `mycosoft_mas/security/event_audit.py` | Security event logging |
| `mycosoft_mas/mcp/progress_notifier.py` | MCP progress emission |

## Verification

- Unit tests: `tests/test_agent_bus.py`, `tests/test_websocket_mixin.py`, `tests/test_a2a_websocket.py`, `tests/test_policy_engine.py`, `tests/test_mcp_progress.py`
- Integration: `scripts/test_agent_bus_integration.py` (when MAS + Redis available)
