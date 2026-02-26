# Agent Bus Migration Guide - February 9, 2026

## Purpose

Guide for migrating agents and integrations to use the WebSocket Agent Bus instead of (or alongside) HTTP polling.

## Prerequisites

- MAS running on VM 192.168.0.188 (port 8001)
- Redis on VM 192.168.0.189 (port 6379)
- Feature flags enabled in environment

## Enabling the Agent Bus

### 1. Enable Agent Bus endpoint

```bash
export MYCA_AGENT_BUS_ENABLED=true
```

Restart MAS. The `/ws/agent-bus` WebSocket endpoint will accept connections.

### 2. Enable agent WebSocket mixin (optional)

For agents that should connect to the bus:

```bash
export MYCA_AGENT_WS_ENABLED=true
```

In agent config:

```python
config = {
    "ws_enabled": True,
    ...
}
```

### 3. Enable A2A WebSocket (optional)

For A2A clients that prefer WebSocket over HTTP:

```bash
export MYCA_A2A_WS_ENABLED=true
```

Connect to `ws://192.168.0.188:8001/a2a/v1/ws` and send JSON messages in SendMessageRequest shape.

### 4. Enable policy engine (recommended for production)

```bash
export MYCA_POLICY_ENGINE_ENABLED=true
```

Events are validated before publish. Blocked events are audited.

## Migration Steps

### From HTTP polling to Agent Bus

**Before (polling):**
```python
async def wait_for_tasks():
    while True:
        r = await http_client.get("/api/tasks/pending")
        tasks = r.json()
        for t in tasks:
            await process(t)
        await asyncio.sleep(5)
```

**After (WebSocket):**
```python
# Agent extends BaseAgent with AgentWebSocketMixin
await self.connect_to_bus(self.agent_id)
await self.send_event("status", "broadcast", {"ready": True})
events = await self.receive_events()
for ev in events:
    if ev.get("type") == "task":
        await process(ev["data"])
```

### From A2A HTTP to A2A WebSocket

**Before (HTTP):**
```python
r = await http_client.post("/a2a/v1/message/send", json=request)
result = r.json()
```

**After (WebSocket):**
```python
async with websockets.connect("ws://192.168.0.188:8001/a2a/v1/ws") as ws:
    await ws.send(json.dumps(request))
    full_response = ""
    while True:
        chunk = await ws.recv()
        data = json.loads(chunk)
        if data.get("done"):
            break
        full_response += data.get("text", "")
```

## Rollback

To disable all new functionality:

```bash
unset MYCA_AGENT_BUS_ENABLED
unset MYCA_AGENT_WS_ENABLED
unset MYCA_A2A_WS_ENABLED
unset MYCA_POLICY_ENGINE_ENABLED
```

Or set each to `false`. Restart MAS.

## Rollout Strategy

1. **Local Dev** – All flags enabled for testing
2. **Sandbox (187)** – Phase 1–2 flags enabled
3. **MAS VM (188)** – Gradual flag enablement with monitoring
4. **Production** – Full enablement after 72h stability

## Troubleshooting

| Issue | Check |
|-------|-------|
| 4003 on connect | Feature flag not enabled |
| Connection refused | MAS not running on 188:8001 |
| No events received | Subscribed channels, Redis connectivity |
| Policy blocks tool_call | Add tool to `myca/skill_permissions/*/PERMISSIONS.json` |
