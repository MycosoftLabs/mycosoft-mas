# Redis Pub/Sub Usage Guide

**Created:** February 12, 2026  
**Status:** Production Ready ✓  
**Redis Server:** `192.168.0.189:6379`

## Overview

The Redis pub/sub system provides real-time messaging across the Mycosoft Multi-Agent System. It enables device telemetry, agent status updates, experiment data streams, and CREP updates to be broadcast to all interested subscribers.

## Key Features

- ✓ Automatic reconnection on connection loss
- ✓ Channel subscription management
- ✓ Health monitoring and statistics
- ✓ Type-safe channel definitions
- ✓ NO MOCK DATA - Real Redis integration

## Available Channels

| Channel | Purpose | Data Type |
|---------|---------|-----------|
| `devices:telemetry` | Device sensor data from MycoBrain, lab equipment | Temperature, humidity, CO2, TVOC, etc. |
| `agents:status` | Agent health updates, task completion, errors | Status, uptime, CPU, tasks completed |
| `experiments:data` | Lab data streams, measurements, observations | Growth rate, biomass, pH, nutrients |
| `crep:live` | Aviation, maritime, satellite, weather updates | Aircraft position, vessel data, satellites |

## Basic Usage

### 1. Publishing Messages

```python
from mycosoft_mas.realtime.redis_pubsub import (
    publish_device_telemetry,
    publish_agent_status,
    publish_experiment_data,
    publish_crep_update,
)

# Publish device telemetry
await publish_device_telemetry(
    device_id="mushroom1",
    telemetry={
        "temperature": 22.5,
        "humidity": 65.2,
        "co2": 450,
        "tvoc": 120,
    },
    source="device_manager",
)

# Publish agent status
await publish_agent_status(
    agent_id="ceo_agent",
    status="healthy",
    details={
        "uptime_seconds": 3600,
        "tasks_completed": 42,
        "cpu_percent": 5.2,
    },
    source="agent_monitor",
)

# Publish experiment data
await publish_experiment_data(
    experiment_id="mycelium_growth_001",
    data={
        "growth_rate": 0.15,
        "biomass": 125.4,
        "ph": 6.8,
        "nutrient_level": "optimal",
    },
    source="lab_sensor",
)

# Publish CREP update
await publish_crep_update(
    category="aircraft",
    data={
        "icao24": "a12345",
        "callsign": "UAL123",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 35000,
        "velocity": 450,
    },
    source="crep_collector",
)
```

### 2. Subscribing to Channels

```python
from mycosoft_mas.realtime.redis_pubsub import (
    RedisPubSubClient,
    Channel,
    PubSubMessage,
)

# Create client
client = RedisPubSubClient()
await client.connect()

# Define message handler
async def handle_device_telemetry(message: PubSubMessage):
    """Handle incoming device telemetry."""
    device_id = message.data.get("device_id")
    telemetry = message.data.get("telemetry", {})
    
    print(f"Device {device_id}: {telemetry}")
    
    # Store in database, trigger alerts, etc.

# Subscribe to channel
await client.subscribe(
    Channel.DEVICES_TELEMETRY.value,
    handle_device_telemetry,
)

# Client will now receive all messages on this channel
# Keep the application running to receive messages
```

### 3. Using the Client Directly

```python
from mycosoft_mas.realtime.redis_pubsub import RedisPubSubClient

# Create and connect
client = RedisPubSubClient()
await client.connect()

# Check connection
if client.is_connected():
    print("Connected to Redis")

# Publish custom message
await client.publish(
    "custom:channel",
    {"event": "something_happened", "value": 123},
    source="my_agent",
)

# Subscribe to custom channel
async def handler(msg):
    print(f"Received: {msg.data}")

await client.subscribe("custom:channel", handler)

# Get statistics
stats = client.get_stats()
print(f"Messages published: {stats['messages_published']}")
print(f"Messages received: {stats['messages_received']}")

# Disconnect when done
await client.disconnect()
```

### 4. Context Manager Usage

```python
from mycosoft_mas.realtime.redis_pubsub import RedisPubSubClient

async with RedisPubSubClient().connection() as client:
    # Use client here
    await client.publish("test:channel", {"data": "value"})
    
# Automatically disconnected after context
```

## Integration Examples

### Device Manager Integration

```python
# In device manager
from mycosoft_mas.realtime.redis_pubsub import publish_device_telemetry

class DeviceManager:
    async def handle_telemetry(self, device_id: str, data: dict):
        """Handle incoming telemetry from devices."""
        # Store in database
        await self.store_telemetry(device_id, data)
        
        # Broadcast via Redis pub/sub for real-time dashboards
        await publish_device_telemetry(
            device_id=device_id,
            telemetry=data,
            source="device_manager",
        )
```

### Agent Health Monitor

```python
# In agent health monitor
from mycosoft_mas.realtime.redis_pubsub import publish_agent_status

class AgentMonitor:
    async def check_agent_health(self, agent_id: str):
        """Check and broadcast agent health."""
        status = await self.get_agent_status(agent_id)
        
        # Broadcast status update
        await publish_agent_status(
            agent_id=agent_id,
            status=status["health"],
            details={
                "uptime": status["uptime"],
                "cpu": status["cpu_percent"],
                "memory": status["memory_mb"],
            },
            source="agent_monitor",
        )
```

### Real-Time Dashboard Subscriber

```python
# In dashboard backend
from mycosoft_mas.realtime.redis_pubsub import RedisPubSubClient, Channel

class DashboardBackend:
    async def start(self):
        """Start subscribing to real-time updates."""
        self.redis_client = RedisPubSubClient()
        await self.redis_client.connect()
        
        # Subscribe to all channels
        await self.redis_client.subscribe(
            Channel.DEVICES_TELEMETRY.value,
            self.handle_device_update,
        )
        await self.redis_client.subscribe(
            Channel.AGENTS_STATUS.value,
            self.handle_agent_update,
        )
        await self.redis_client.subscribe(
            Channel.EXPERIMENTS_DATA.value,
            self.handle_experiment_update,
        )
    
    async def handle_device_update(self, message):
        """Forward device updates to connected WebSocket clients."""
        await self.websocket_hub.broadcast(
            "device_update",
            message.data,
        )
```

## Configuration

### Environment Variables

```bash
# Redis connection (default: VM 189)
REDIS_HOST=192.168.0.189
REDIS_PORT=6379
REDIS_DB=0
```

### Custom Redis URL

```python
# Use custom Redis URL
client = RedisPubSubClient(
    redis_url="redis://custom-host:6379/1"
)
```

## Connection Management

### Automatic Reconnection

The client automatically attempts to reconnect on connection loss:

```python
client = RedisPubSubClient(
    max_reconnect_attempts=5,  # Try up to 5 times
    reconnect_delay=2.0,        # Wait 2s between attempts
)
```

### Health Checking

```python
# Check if connected
if client.is_connected():
    print("Connected")

# Get connection statistics
stats = client.get_stats()
print(f"Connected: {stats['connected']}")
print(f"Connection errors: {stats['connection_errors']}")
print(f"Last error: {stats['last_error']}")
```

## Testing

### Quick Test

```bash
cd scripts
python quick_redis_test.py
```

Expected output:
```
[OK] Ping: True
[OK] Published to test:channel, subscribers: 0
[OK] Published to devices:telemetry
[OK] Published to agents:status
[OK] Published to experiments:data
[OK] Published to crep:live
[SUCCESS] All Redis pub/sub operations successful!
```

### Verification

```bash
python scripts/verify_redis_pubsub.py
```

## Troubleshooting

### Cannot connect to Redis

**Error:** `Failed to connect to Redis: Connection refused`

**Solution:**
1. Verify Redis is running on VM 189:
   ```bash
   ssh mycosoft@192.168.0.189
   docker ps | grep redis
   ```

2. Check firewall allows port 6379:
   ```bash
   telnet 192.168.0.189 6379
   ```

3. Verify Redis is bound to 0.0.0.0 (not just 127.0.0.1)

### Messages not received

**Issue:** Published messages don't arrive at subscribers

**Possible causes:**
1. Subscriber connected after message was published (pub/sub is fire-and-forget)
2. Subscriber callback threw an exception
3. Different Redis database numbers (check REDIS_DB)

**Solution:**
- Add logging to your message handlers
- Check client stats: `client.get_stats()`
- Verify channels match exactly (case-sensitive)

### Slow performance

**Issue:** Message delivery is slow

**Solution:**
1. Check network latency to VM 189:
   ```bash
   ping 192.168.0.189
   ```

2. Monitor Redis memory usage:
   ```bash
   ssh mycosoft@192.168.0.189
   docker exec redis redis-cli INFO memory
   ```

3. Consider using local Redis for dev (not recommended for production)

## Best Practices

### 1. Channel Naming

Use the predefined `Channel` enum for system channels:

```python
# GOOD
from mycosoft_mas.realtime.redis_pubsub import Channel
await client.subscribe(Channel.DEVICES_TELEMETRY.value, handler)

# AVOID
await client.subscribe("devices:telemetry", handler)  # Typo-prone
```

### 2. Message Size

Keep messages small (< 1MB). For large data:
- Store in database/blob storage
- Publish reference/ID via Redis pub/sub

```python
# GOOD
await client.publish("data:ready", {
    "data_id": "exp_001",
    "location": "blob://experiments/001.json"
})

# AVOID
await client.publish("data:ready", {
    "huge_data": [...10MB array...]
})
```

### 3. Error Handling

Always handle errors in message callbacks:

```python
async def safe_handler(message: PubSubMessage):
    try:
        # Process message
        await process(message.data)
    except Exception as e:
        logger.error(f"Handler error: {e}")
        # Don't re-raise - would kill the listener task
```

### 4. Graceful Shutdown

Always disconnect clients on shutdown:

```python
import signal

async def shutdown(client):
    await client.disconnect()

# Register shutdown handler
signal.signal(signal.SIGTERM, lambda s, f: asyncio.run(shutdown(client)))
```

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│   Publisher     │         │    Redis     │         │   Subscriber    │
│   (Agent/Device)│────────▶│  VM 189:6379 │────────▶│   (Dashboard)   │
└─────────────────┘         └──────────────┘         └─────────────────┘
                                    │
                                    ├─ devices:telemetry
                                    ├─ agents:status
                                    ├─ experiments:data
                                    └─ crep:live
```

## Related Documentation

- `docs/SYSTEM_REGISTRY_FEB04_2026.md` - Full system architecture
- `mycosoft_mas/realtime/redis_pubsub.py` - Implementation source
- `mycosoft_mas/realtime/pubsub.py` - WebSocket integration
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` - VM configuration

## Status

✓ **Production Ready**
- All 4 channels tested and working
- Automatic reconnection implemented
- Connection management validated
- Real Redis integration confirmed (VM 192.168.0.189:6379)

Last verified: February 12, 2026
