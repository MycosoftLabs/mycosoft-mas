# Agent Event Bus Usage Guide

**Created:** February 9, 2026  
**Status:** Production Ready (feature-flagged)  
**Endpoint:** `ws://host/ws/agent-bus` (when `MYCA_AGENT_BUS_ENABLED=true`)

## Overview

The Agent Event Bus provides real-time WebSocket messaging for agent-to-agent (A2A) communication. It extends the existing Redis pub/sub and WebSocketHub infrastructure.

## Enabling the Agent Bus

Set in `.env` or environment:

```
MYCA_AGENT_BUS_ENABLED=true
```

## Connection Flow

1. Connect to `ws://192.168.0.188:8001/ws/agent-bus` (MAS VM)
2. Send **first message** (JSON text):

```json
{
  "agent_id": "lab_agent",
  "channels": ["agents:status", "agents:tasks", "agents:tool_calls"]
}
```

3. Receive `{"type": "connected", "payload": {"connection_id": "...", "agent_id": "lab_agent"}}`
4. Send events or heartbeats in the receive loop

## Event Types

| Type      | Redis Channel        | Use Case                         |
|-----------|----------------------|----------------------------------|
| `task`    | `agents:tasks`       | Delegate work to another agent   |
| `result`  | `agents:status`      | Task completion, outcome         |
| `alert`   | `agents:status`      | Warnings, escalation             |
| `heartbeat` | N/A (local only)   | Keep session alive               |
| `tool_call` | `agents:tool_calls` | Tool invocation events           |
| `status`  | `agents:status`      | General status updates           |

## Sending Events

**Format 1 – Event type as message type:**
```json
{
  "type": "task",
  "to_agent": "dev_agent",
  "payload": {"task_id": "t1", "description": "Fix bug in auth"}
}
```

**Format 2 – Wrapped event:**
```json
{
  "type": "event",
  "event_type": "task",
  "to_agent": "broadcast",
  "payload": {"message": "Lab experiment complete"}
}
```

## Related Components

- **Event schema:** `mycosoft_mas.realtime.event_schema.AgentEvent`
- **Session manager:** `mycosoft_mas.realtime.agent_session.AgentSessionManager`
- **Redis channels:** `agents:status`, `agents:tasks`, `agents:tool_calls` (see `redis_pubsub.py`)
- **WebSocketHub:** Local broadcast to subscribed connections

## Redis Bridge

Events are published to both:

1. **Redis pub/sub** – for cross-instance subscribers and other services
2. **WebSocketHub** – for local WebSocket clients subscribed to the same channels

## See Also

- `docs/REDIS_PUBSUB_USAGE_FEB12_2026.md` – Redis pub/sub usage
- `docs/API_CATALOG_FEB04_2026.md` – API catalog
- Plan: WebSocket Agent Bus Integration (Phase 1 complete)
