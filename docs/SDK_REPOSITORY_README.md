# NatureOS Developer SDK

**The official SDK for building applications on the NatureOS platform.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![npm version](https://img.shields.io/npm/v/@mycosoft/natureos-sdk.svg)](https://www.npmjs.com/package/@mycosoft/natureos-sdk)

## Overview

The NatureOS Developer SDK provides a comprehensive toolkit for developers to build applications that interact with NatureOS, the cloud platform for environmental monitoring and IoT device management. The SDK offers type-safe clients, utilities, and abstractions for seamless integration with NatureOS services.

## Features

- **Device Management**: Register, configure, and monitor IoT devices
- **Sensor Data Access**: Real-time and historical sensor data retrieval
- **Environmental Monitoring**: Access to environmental data streams
- **Command Execution**: Send commands to devices remotely
- **Analytics**: Data analysis and visualization utilities
- **Multi-tenant Support**: Built-in support for tenant isolation
- **Offline Mode**: Local caching and offline operation
- **Type Safety**: Full TypeScript and Python type support

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
    api_key="your_api_key"
)

# List devices
devices = await client.list_devices()
for device in devices:
    print(f"{device.name} - {device.status}")

# Get sensor data
data = await client.get_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature"
)

# Send command
result = await client.send_command(
    device_id="esp32-001",
    command_type="set_mosfet",
    parameters={"channel": 1, "state": "on"}
)
```

### TypeScript

```typescript
import { NatureOSClient } from '@mycosoft/natureos-sdk';

const client = new NatureOSClient({
  apiUrl: 'http://localhost:8002',
  apiKey: 'your_api_key'
});

// List devices
const devices = await client.listDevices();
devices.forEach(device => {
  console.log(`${device.name} - ${device.status}`);
});

// Get sensor data
const data = await client.getSensorData({
  deviceId: 'esp32-001',
  sensorType: 'temperature'
});

// Send command
const result = await client.sendCommand({
  deviceId: 'esp32-001',
  commandType: 'set_mosfet',
  parameters: { channel: 1, state: 'on' }
});
```

## Documentation

- **[Full Documentation](./docs/SDK_README.md)**: Comprehensive guide
- **[Database Schema](./docs/SDK_DATABASE_SCHEMA.md)**: Database structure
- **[Integration Guide](../docs/INTEGRATION_GUIDE.md)**: Integration with other systems
- **[API Reference](./docs/API.md)**: Complete API documentation

## Key Features

### Device Management

```python
# List all devices
devices = await client.list_devices(device_type="esp32", status="online")

# Get device details
device = await client.get_device(device_id="esp32-001")

# Register new device
device = await client.register_device(
    device_id="esp32-001",
    name="My Device",
    device_type="esp32"
)

# Update device configuration
await client.update_device_config(
    device_id="esp32-001",
    config={"telemetry_interval": 60}
)
```

### Sensor Data

```python
# Get historical data
data = await client.get_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature",
    start_time=datetime.now() - timedelta(hours=24)
)

# Stream real-time data
async for reading in client.stream_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature"
):
    print(f"Temperature: {reading.value}°C")
```

### MycoBrain Integration

Specialized methods for MycoBrain devices:

```python
# Register MycoBrain device
device = await client.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB-2024-001",
    name="MycoBrain Lab Unit",
    firmware_version="2.1.0"
)

# Get MycoBrain telemetry
telemetry = await client.get_mycobrain_telemetry(
    device_id="mycobrain-001"
)

# Send MycoBrain command
result = await client.send_mycobrain_command(
    device_id="mycobrain-001",
    command_type="set_mosfet",
    parameters={"channel": 1, "state": "on"}
)
```

## Integrations

### NLM Integration

Use with NLM for intelligent data processing:

```python
from natureos_sdk import NatureOSClient
from nlm import NLMClient

natureos = NatureOSClient(...)
nlm = NLMClient(...)

data = await natureos.get_sensor_data(device_id="esp32-001")
insights = await nlm.process_environmental_data(
    temperature=data[0].value,
    humidity=data[1].value
)
```

### MAS Integration

Use with Multi-Agent System:

```python
from natureos_sdk import NatureOSClient
from mycosoft_mas.integrations import UnifiedIntegrationManager

natureos = NatureOSClient(...)
manager = UnifiedIntegrationManager()
await manager.initialize()

devices = await manager.natureos.list_devices()
```

## Configuration

### Environment Variables

```bash
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_api_key
NATUREOS_TENANT_ID=your_tenant_id  # Optional
```

### Client Configuration

```python
from natureos_sdk import NatureOSClient, ClientConfig

config = ClientConfig(
    api_url="http://localhost:8002",
    api_key="your_api_key",
    timeout=30,
    max_retries=3
)

client = NatureOSClient(config=config)
```

## Error Handling

```python
from natureos_sdk import NatureOSError

try:
    device = await client.get_device(device_id="esp32-001")
except NatureOSError as e:
    if e.status_code == 404:
        print("Device not found")
    elif e.status_code == 401:
        print("Authentication failed")
```

## Examples

See [examples/](./examples/) directory for complete examples:

- Device monitoring
- Data logging
- Automated control
- Web application integration

## Development

### Project Structure

```
sdk/
├── natureos_sdk/           # Python package
│   ├── client.py          # Main client
│   ├── models.py          # Data models
│   ├── exceptions.py      # Error classes
│   └── database.py        # Database utilities
├── @mycosoft/             # TypeScript package
│   ├── src/               # Source code
│   └── dist/              # Compiled output
├── examples/               # Code examples
├── tests/                  # Test suite
└── docs/                   # Documentation
```

### Running Tests

```bash
# Python
pytest

# TypeScript
npm test
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](./LICENSE) file for details.

## Support

- **Documentation**: [docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/MycosoftLabs/sdk/issues)
- **Email**: support@mycosoft.com

