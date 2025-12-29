# NatureOS Developer SDK

**The official SDK for building applications on the NatureOS platform.**

## Overview

The NatureOS Developer SDK provides a comprehensive toolkit for developers to build applications that interact with NatureOS, the cloud platform for environmental monitoring and IoT device management. The SDK offers type-safe clients, utilities, and abstractions for seamless integration with NatureOS services.

## Features

### Core Capabilities
- **Device Management**: Register, configure, and monitor IoT devices
- **Sensor Data Access**: Real-time and historical sensor data retrieval
- **Environmental Monitoring**: Access to environmental data streams
- **Command Execution**: Send commands to devices remotely
- **Analytics**: Data analysis and visualization utilities
- **Multi-tenant Support**: Built-in support for tenant isolation

### Language Support
- **Python**: Full-featured async client library
- **TypeScript/JavaScript**: Node.js and browser support
- **REST API**: Language-agnostic HTTP API

### Integration Ready
- **NLM Integration**: Direct integration with Nature Learning Model
- **MAS Integration**: Multi-Agent System compatibility
- **Website Integration**: Public API endpoints
- **Database Integration**: PostgreSQL, Redis, Qdrant support

## Installation

### Python

```bash
pip install natureos-sdk
```

Or from source:

```bash
git clone https://github.com/MycosoftLabs/sdk.git
cd sdk
pip install -e .
```

### TypeScript/JavaScript

```bash
npm install @mycosoft/natureos-sdk
```

Or with yarn:

```bash
yarn add @mycosoft/natureos-sdk
```

## Quick Start

### Python

```python
from natureos_sdk import NatureOSClient

# Initialize client
client = NatureOSClient(
    api_url="http://localhost:8002",
    api_key="your_api_key",
    tenant_id="your_tenant_id"  # Optional
)

# List devices
devices = await client.list_devices()
for device in devices:
    print(f"{device.name} - {device.status}")

# Get sensor data
data = await client.get_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature",
    start_time=datetime.now() - timedelta(hours=24)
)

# Send command to device
result = await client.send_command(
    device_id="esp32-001",
    command_type="set_mosfet",
    parameters={"channel": 1, "state": "on"}
)
```

### TypeScript

```typescript
import { NatureOSClient } from '@mycosoft/natureos-sdk';

// Initialize client
const client = new NatureOSClient({
  apiUrl: 'http://localhost:8002',
  apiKey: 'your_api_key',
  tenantId: 'your_tenant_id' // Optional
});

// List devices
const devices = await client.listDevices();
devices.forEach(device => {
  console.log(`${device.name} - ${device.status}`);
});

// Get sensor data
const data = await client.getSensorData({
  deviceId: 'esp32-001',
  sensorType: 'temperature',
  startTime: new Date(Date.now() - 24 * 60 * 60 * 1000)
});

// Send command
const result = await client.sendCommand({
  deviceId: 'esp32-001',
  commandType: 'set_mosfet',
  parameters: { channel: 1, state: 'on' }
});
```

## API Reference

### Device Management

#### List Devices

```python
devices = await client.list_devices(
    device_type="esp32",  # Optional filter
    status="online",      # Optional filter
    limit=100            # Optional limit
)
```

#### Get Device

```python
device = await client.get_device(device_id="esp32-001")
```

#### Register Device

```python
device = await client.register_device(
    device_id="esp32-001",
    name="My Device",
    device_type="esp32",
    location={"lat": 45.5, "lon": -122.6},
    metadata={"firmware_version": "1.0.0"}
)
```

#### Update Device Configuration

```python
config = await client.update_device_config(
    device_id="esp32-001",
    config={
        "telemetry_interval": 60,
        "sensor_config": {...}
    }
)
```

### Sensor Data

#### Get Sensor Data

```python
data = await client.get_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature",  # Optional
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    limit=1000
)
```

#### Stream Real-time Data

```python
async for reading in client.stream_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature"
):
    print(f"Temperature: {reading.value}°C at {reading.timestamp}")
```

### Commands

#### Send Command

```python
result = await client.send_command(
    device_id="esp32-001",
    command_type="set_mosfet",
    parameters={
        "channel": 1,
        "state": "on"
    }
)
```

#### Get Command Status

```python
status = await client.get_command_status(
    device_id="esp32-001",
    command_id="cmd-123"
)
```

### MycoBrain Integration

The SDK includes specialized methods for MycoBrain devices:

```python
# Register MycoBrain device
device = await client.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB-2024-001",
    name="MycoBrain Lab Unit",
    firmware_version="2.1.0",
    location={"lat": 45.5, "lon": -122.6}
)

# Get MycoBrain devices
devices = await client.get_mycobrain_devices(status="online")

# Get telemetry
telemetry = await client.get_mycobrain_telemetry(
    device_id="mycobrain-001",
    start_time=datetime.now() - timedelta(hours=24)
)

# Send MycoBrain command
result = await client.send_mycobrain_command(
    device_id="mycobrain-001",
    command_type="set_mosfet",
    parameters={"channel": 1, "state": "on"}
)
```

## Configuration

### Environment Variables

```bash
# Required
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_api_key

# Optional
NATUREOS_TENANT_ID=your_tenant_id
NATUREOS_TIMEOUT=30
NATUREOS_MAX_RETRIES=3
```

### Client Configuration

```python
from natureos_sdk import NatureOSClient, ClientConfig

config = ClientConfig(
    api_url="http://localhost:8002",
    api_key="your_api_key",
    tenant_id="your_tenant_id",
    timeout=30,
    max_retries=3,
    retry_delay=1.0
)

client = NatureOSClient(config=config)
```

## Error Handling

```python
from natureos_sdk import NatureOSClient, NatureOSError

try:
    device = await client.get_device(device_id="esp32-001")
except NatureOSError as e:
    if e.status_code == 404:
        print("Device not found")
    elif e.status_code == 401:
        print("Authentication failed")
    else:
        print(f"Error: {e.message}")
```

## Integrations

### NLM Integration

Use the SDK with NLM for intelligent data processing:

```python
from natureos_sdk import NatureOSClient
from nlm import NLMClient

natureos = NatureOSClient(...)
nlm = NLMClient(...)

# Get sensor data
data = await natureos.get_sensor_data(device_id="esp32-001")

# Process with NLM
insights = await nlm.process_environmental_data(
    temperature=data[0].value,
    humidity=data[1].value,
    location=device.location
)
```

### MAS Integration

Integrate with the Multi-Agent System:

```python
from natureos_sdk import NatureOSClient
from mycosoft_mas.integrations import UnifiedIntegrationManager

natureos = NatureOSClient(...)
manager = UnifiedIntegrationManager()

await manager.initialize()

# Use NatureOS through unified manager
devices = await manager.natureos.list_devices()
```

### Website Integration

The SDK can be used in web applications:

```typescript
// Browser usage
import { NatureOSClient } from '@mycosoft/natureos-sdk/browser';

const client = new NatureOSClient({
  apiUrl: 'https://api.natureos.com',
  apiKey: 'your_api_key'
});

// Use in React component
function DeviceList() {
  const [devices, setDevices] = useState([]);
  
  useEffect(() => {
    client.listDevices().then(setDevices);
  }, []);
  
  return <div>{/* Render devices */}</div>;
}
```

## Database Integration

The SDK supports direct database access for advanced use cases:

```python
from natureos_sdk.database import NatureOSDatabase

db = NatureOSDatabase(
    database_url="postgresql://user:pass@localhost:5432/natureos"
)

# Query devices directly
devices = await db.query_devices(
    "SELECT * FROM devices WHERE status = 'online'"
)

# Insert sensor data
await db.insert_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature",
    value=22.5,
    timestamp=datetime.now()
)
```

## Examples

### Example 1: Monitor Device Health

```python
import asyncio
from natureos_sdk import NatureOSClient

async def monitor_devices():
    client = NatureOSClient(...)
    
    while True:
        devices = await client.list_devices()
        
        for device in devices:
            if device.status != "online":
                print(f"Alert: {device.name} is {device.status}")
            
            # Check last seen time
            if device.last_seen:
                time_since_seen = datetime.now() - device.last_seen
                if time_since_seen > timedelta(hours=1):
                    print(f"Warning: {device.name} hasn't reported in {time_since_seen}")
        
        await asyncio.sleep(60)  # Check every minute

asyncio.run(monitor_devices())
```

### Example 2: Data Logger

```python
from natureos_sdk import NatureOSClient
import csv

async def log_sensor_data():
    client = NatureOSClient(...)
    
    with open('sensor_data.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'device_id', 'sensor_type', 'value'])
        
        devices = await client.list_devices()
        
        for device in devices:
            data = await client.get_sensor_data(
                device_id=device.id,
                start_time=datetime.now() - timedelta(hours=24)
            )
            
            for reading in data:
                writer.writerow([
                    reading.timestamp,
                    device.id,
                    reading.sensor_type,
                    reading.value
                ])

asyncio.run(log_sensor_data())
```

### Example 3: Automated Control

```python
from natureos_sdk import NatureOSClient

async def automated_control():
    client = NatureOSClient(...)
    
    # Get current sensor readings
    data = await client.get_sensor_data(
        device_id="mycobrain-001",
        sensor_type="temperature"
    )
    
    current_temp = data[-1].value if data else None
    
    if current_temp and current_temp > 25:
        # Temperature too high, turn on cooling
        await client.send_command(
            device_id="mycobrain-001",
            command_type="set_mosfet",
            parameters={"channel": 2, "state": "on"}
        )
        print("Cooling activated")
    elif current_temp and current_temp < 18:
        # Temperature too low, turn on heating
        await client.send_command(
            device_id="mycobrain-001",
            command_type="set_mosfet",
            parameters={"channel": 1, "state": "on"}
        )
        print("Heating activated")

asyncio.run(automated_control())
```

## Testing

```python
from natureos_sdk import NatureOSClient
from natureos_sdk.testing import MockNatureOSClient

# Use mock client for testing
client = MockNatureOSClient()

# Test your code
devices = await client.list_devices()
assert len(devices) > 0
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](./LICENSE) file for details.

## Support

- **Documentation**: [https://github.com/MycosoftLabs/sdk/docs](https://github.com/MycosoftLabs/sdk/docs)
- **Issues**: [https://github.com/MycosoftLabs/sdk/issues](https://github.com/MycosoftLabs/sdk/issues)
- **Email**: support@mycosoft.com

