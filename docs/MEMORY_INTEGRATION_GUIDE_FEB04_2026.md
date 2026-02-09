# Memory Integration Guide
## Created: February 4, 2026

> **📌 UPDATED**: This guide remains valid. Additional integrations have been added as of February 5, 2026:
> - **Brain API Integration**: See [MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)
> - **Website UI Components**: See [MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md](./MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md)
> - **Complete System Reference**: See [MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)

---

## Overview

This guide explains how to integrate with the Mycosoft Unified Memory System from any system or programming language.

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    Unified Memory System                         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚   Redis     â”‚  â”‚ PostgreSQL  â”‚  â”‚   Qdrant    â”‚             â”‚
â”‚  â”‚  (Cache)    â”‚  â”‚ (Persistent)â”‚  â”‚  (Vectors)  â”‚             â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â”‚         â”‚                â”‚                â”‚                      â”‚
â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                      â”‚
â”‚                          â”‚                                       â”‚
â”‚              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                          â”‚
â”‚              â”‚    Memory API         â”‚                          â”‚
â”‚              â”‚  /api/memory/*        â”‚                          â”‚
â”‚              â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                          â”‚
â”‚                          â”‚                                       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚                      â”‚                      â”‚
â”Œâ”€â”€â”€â–¼â”€â”€â”€â”            â”Œâ”€â”€â”€â”€â–¼â”€â”€â”€â”€â”            â”Œâ”€â”€â”€â”€â–¼â”€â”€â”€â”€â”
â”‚  MAS  â”‚            â”‚ Website â”‚            â”‚ NatureOSâ”‚
â”‚Python â”‚            â”‚TypeScriptâ”‚           â”‚   C#    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”˜            â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Memory Scopes

| Scope | TTL | Backend | Use Case |
|-------|-----|---------|----------|
| `conversation` | 1 hour | Redis | Dialog context |
| `user` | Permanent | PostgreSQL | User preferences |
| `agent` | 24 hours | Redis | Agent working memory |
| `system` | Permanent | PostgreSQL | Global config |
| `ephemeral` | 1 minute | In-memory | Scratch space |
| `device` | Permanent | PostgreSQL | Device state |
| `experiment` | Permanent | PostgreSQL | Scientific data |
| `workflow` | 7 days | Redis + PostgreSQL | N8N workflows |

## Integration Methods

### 1. Python (Direct Import)

```python
from mycosoft_mas.integrations.unified_memory_bridge import (
    UnifiedMemoryBridge, MemoryScope, get_memory_bridge
)

async def example():
    bridge = get_memory_bridge()
    
    # Write memory
    await bridge.memory_write(
        scope=MemoryScope.USER,
        namespace="user_123",
        key="preferences",
        value={"theme": "dark", "language": "en"}
    )
    
    # Read memory
    prefs = await bridge.memory_read(
        scope=MemoryScope.USER,
        namespace="user_123",
        key="preferences"
    )
    
    # List keys
    keys = await bridge.memory_list_keys(
        scope=MemoryScope.USER,
        namespace="user_123"
    )
```

### 2. HTTP REST API

```bash
# Write memory
curl -X POST http://192.168.0.188:8001/api/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "user",
    "namespace": "user_123",
    "key": "preferences",
    "value": {"theme": "dark"}
  }'

# Read memory
curl -X POST http://192.168.0.188:8001/api/memory/read \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "user",
    "namespace": "user_123",
    "key": "preferences"
  }'

# List keys
curl http://192.168.0.188:8001/api/memory/list/user/user_123
```

### 3. TypeScript/JavaScript

```typescript
// Website frontend
const memoryClient = {
  async write(scope: string, namespace: string, key: string, value: any) {
    const res = await fetch('/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, namespace, key, value, action: 'write' })
    });
    return res.json();
  },
  
  async read(scope: string, namespace: string, key: string) {
    const res = await fetch('/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, namespace, key, action: 'read' })
    });
    const data = await res.json();
    return data.value;
  }
};

// Usage
await memoryClient.write('user', 'user_123', 'theme', 'dark');
const theme = await memoryClient.read('user', 'user_123', 'theme');
```

### 4. C# (.NET Core)

```csharp
public class MemoryBridgeService
{
    private readonly HttpClient _client;
    private readonly string _baseUrl;
    
    public async Task<T> ReadAsync<T>(string scope, string ns, string key)
    {
        var request = new { scope, @namespace = ns, key };
        var response = await _client.PostAsJsonAsync(
            $"{_baseUrl}/api/memory/read", request);
        var result = await response.Content.ReadFromJsonAsync<MemoryResponse<T>>();
        return result.Value;
    }
    
    public async Task WriteAsync(string scope, string ns, string key, object value)
    {
        var request = new { scope, @namespace = ns, key, value };
        await _client.PostAsJsonAsync($"{_baseUrl}/api/memory/write", request);
    }
}
```

### 5. C++/Arduino (MycoBrain)

```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

void writeMemory(const char* scope, const char* ns, const char* key, 
                 const JsonDocument& value) {
    HTTPClient http;
    http.begin("http://192.168.0.188:8001/api/memory/write");
    http.addHeader("Content-Type", "application/json");
    
    StaticJsonDocument<512> doc;
    doc["scope"] = scope;
    doc["namespace"] = ns;
    doc["key"] = key;
    doc["value"] = value;
    
    String json;
    serializeJson(doc, json);
    http.POST(json);
    http.end();
}
```

## Cryptographic Integrity

All memory writes are automatically recorded in the cryptographic ledger:

1. **SHA256 Hash**: Data is hashed for integrity verification
2. **HMAC Signature**: Authenticated hash prevents tampering
3. **Dual Write**: Saved to PostgreSQL and JSONL file
4. **Block Commits**: Entries are committed to blocks with Merkle roots

## Best Practices

### 1. Choose Correct Scope

```python
# For user preferences (permanent)
await bridge.memory_write(MemoryScope.USER, "user_123", "settings", data)

# For conversation context (short-lived)
await bridge.memory_write(MemoryScope.CONVERSATION, "conv_456", "history", messages)

# For device telemetry (permanent with timestamp)
await bridge.memory_write(MemoryScope.DEVICE, "sporebase-001", "temperature", {
    "value": 23.5,
    "timestamp": datetime.now().isoformat()
})
```

### 2. Use Namespaces

```python
# User-scoped data
namespace = f"user_{user_id}"

# Agent-scoped data
namespace = f"agent_{agent_name}"

# Device-scoped data
namespace = f"device_{device_id}"
```

### 3. Handle Errors

```python
try:
    result = await bridge.memory_write(scope, namespace, key, value)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        logger.error("Memory service unavailable")
    raise
```

### 4. Check Health

```python
health = await bridge.health_check()
if health["overall"] != "healthy":
    logger.warning(f"Memory system degraded: {health['services']}")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAS_URL` | `http://192.168.0.188:8001` | MAS API URL |
| `MINDEX_URL` | `http://192.168.0.189:8000` | MINDEX API URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |

## Related Documentation

- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [API Catalog](./API_CATALOG_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)
