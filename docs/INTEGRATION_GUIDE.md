# Integration Guide: NLM, SDK, NatureOS, Website, and MAS

This guide documents how NLM and SDK integrate with NatureOS, the website, and the Multi-Agent System (MAS).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Mycosoft Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Website    │  │     MAS      │  │  NatureOS    │    │
│  │  (Next.js)   │  │ (Orchestrator)│  │  (Cloud API) │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                                │
│         ┌──────────────────┼──────────────────┐            │
│         │                  │                  │            │
│  ┌──────▼───────┐  ┌───────▼───────┐  ┌──────▼───────┐    │
│  │     NLM      │  │      SDK      │  │   Database   │    │
│  │  (Model API) │  │ (Client Lib)  │  │ (PostgreSQL) │    │
│  └──────────────┘  └───────────────┘  └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## NLM Integrations

### NLM ↔ NatureOS Integration

**Purpose**: NLM processes real-time sensor data from NatureOS devices to generate insights and predictions.

**Data Flow**:
1. NatureOS devices send sensor data to NatureOS API
2. NLM ingests data via NatureOS API
3. NLM processes data through multi-modal encoders
4. NLM updates knowledge graph with new observations
5. NLM generates predictions and recommendations
6. Results available via NLM API

**Implementation**:

```python
# NLM side
from nlm.integrations.natureos import NatureOSIngester

ingester = NatureOSIngester(
    natureos_api_url=os.getenv("NATUREOS_API_URL"),
    nlm_client=nlm_client
)

# Start continuous ingestion
await ingester.start_ingestion(
    device_ids=["mycobrain-001", "mycobrain-002"],
    sensor_types=["temperature", "humidity", "co2"]
)

# Process batch of data
observations = await ingester.process_batch(
    start_time=datetime.now() - timedelta(hours=24)
)
```

**Database Schema**:
- `nlm.integrations.integration_state`: Tracks NatureOS sync state
- `nlm.knowledge.observations`: Stores ingested sensor data
- `nlm.knowledge.entities`: Entities derived from NatureOS data

### NLM ↔ MINDEX Integration

**Purpose**: NLM learns from mycological species data in MINDEX to enhance predictions.

**Data Flow**:
1. NLM queries MINDEX for species data
2. NLM processes species information (taxonomy, habitats, growth conditions)
3. NLM updates knowledge graph with species entities
4. NLM uses species knowledge for predictions

**Implementation**:

```python
# NLM side
from nlm.integrations.mindex import MINDEXConnector

connector = MINDEXConnector(
    mindex_api_url=os.getenv("MINDEX_API_URL"),
    nlm_client=nlm_client
)

# Sync species data
await connector.sync_species_data(
    filters={"habitat": "temperate_forest"},
    batch_size=100
)

# Query species with NLM context
species = await connector.query_species_with_nlm(
    query="species that thrive in high humidity",
    nlm_context={"location": "Pacific Northwest"}
)
```

**Database Schema**:
- `nlm.knowledge.entities`: Species entities from MINDEX
- `nlm.knowledge.relations`: Species-habitat relationships
- `nlm.integrations.sync_log`: MINDEX sync history

### NLM ↔ MAS Integration

**Purpose**: NLM provides intelligent decision support to MAS agents.

**Data Flow**:
1. MAS agent sends query to NLM
2. NLM processes query with context
3. NLM generates response (prediction, recommendation, knowledge)
4. MAS agent uses response for decision-making

**Implementation**:

```python
# MAS side
from mycosoft_mas.integrations import UnifiedIntegrationManager

manager = UnifiedIntegrationManager()
await manager.initialize()

# Query NLM from agent
response = await manager.nlm.query(
    query="What are optimal conditions for Pleurotus ostreatus?",
    context={
        "agent_id": "mycology_agent",
        "current_conditions": {"temp": 22, "humidity": 65}
    }
)

# NLM side (service registration)
from nlm.integrations.mas import MASConnector

connector = MASConnector(
    mas_api_url=os.getenv("MAS_API_URL"),
    nlm_client=nlm_client
)

# Register as MAS service
await connector.register_service(
    service_name="nlm",
    capabilities=["prediction", "recommendation", "knowledge_query"]
)
```

**API Endpoints**:
- `POST /api/v1/mas/query`: Process agent query
- `GET /api/v1/mas/services`: List registered services
- `POST /api/v1/mas/register`: Register NLM service

### NLM ↔ Website Integration

**Purpose**: Website provides public API access to NLM capabilities.

**Data Flow**:
1. Website user makes request
2. Website API calls NLM API
3. NLM processes request
4. Results returned to website
5. Website displays results to user

**Implementation**:

```typescript
// Website side (Next.js API route)
import { NLMClient } from '@mycosoft/nlm-sdk';

export async function POST(request: Request) {
  const { query, context } = await request.json();
  
  const nlm = new NLMClient({
    apiUrl: process.env.NLM_API_URL,
    apiKey: process.env.NLM_API_KEY
  });
  
  const result = await nlm.queryKnowledgeGraph({
    query,
    context
  });
  
  return Response.json(result);
}
```

**Public Endpoints**:
- `POST /api/v1/public/knowledge/query`: Public knowledge queries
- `GET /api/v1/public/predictions/{type}`: Public predictions
- `GET /api/v1/public/docs`: API documentation

## SDK Integrations

### SDK ↔ NatureOS Integration

**Purpose**: SDK provides client library for NatureOS API access.

**Implementation**:

```python
from natureos_sdk import NatureOSClient

client = NatureOSClient(
    api_url=os.getenv("NATUREOS_API_URL"),
    api_key=os.getenv("NATUREOS_API_KEY")
)

# Standard SDK usage
devices = await client.list_devices()
data = await client.get_sensor_data(device_id="esp32-001")
```

**Features**:
- Automatic retry logic
- Rate limiting
- Caching support
- Offline mode

### SDK ↔ NLM Integration

**Purpose**: SDK can integrate with NLM for intelligent data processing.

**Implementation**:

```python
from natureos_sdk import NatureOSClient
from nlm import NLMClient

natureos = NatureOSClient(...)
nlm = NLMClient(...)

# Get sensor data
sensor_data = await natureos.get_sensor_data(
    device_id="mycobrain-001",
    start_time=datetime.now() - timedelta(hours=24)
)

# Process with NLM
insights = await nlm.process_environmental_data(
    temperature=sensor_data[0].value,
    humidity=sensor_data[1].value,
    location=device.location
)

# Get recommendations
recommendations = await nlm.recommend(
    scenario="optimal_growth",
    constraints={"device_id": "mycobrain-001"}
)
```

### SDK ↔ MAS Integration

**Purpose**: SDK can be used by MAS agents to interact with NatureOS.

**Implementation**:

```python
# MAS agent using SDK
from natureos_sdk import NatureOSClient
from mycosoft_mas.agents import BaseAgent

class MycologyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.natureos = NatureOSClient(
            api_url=os.getenv("NATUREOS_API_URL"),
            api_key=os.getenv("NATUREOS_API_KEY")
        )
    
    async def monitor_growth_conditions(self, device_id: str):
        data = await self.natureos.get_sensor_data(device_id=device_id)
        # Process data and make decisions
```

### SDK ↔ Website Integration

**Purpose**: Website can use SDK in server-side API routes or client-side.

**Implementation**:

```typescript
// Server-side (Next.js API route)
import { NatureOSClient } from '@mycosoft/natureos-sdk';

export async function GET(request: Request) {
  const client = new NatureOSClient({
    apiUrl: process.env.NATUREOS_API_URL,
    apiKey: process.env.NATUREOS_API_KEY
  });
  
  const devices = await client.listDevices();
  return Response.json(devices);
}

// Client-side (React component)
'use client';

import { NatureOSClient } from '@mycosoft/natureos-sdk/browser';

export function DeviceList() {
  const [devices, setDevices] = useState([]);
  
  useEffect(() => {
    const client = new NatureOSClient({
      apiUrl: '/api/natureos', // Proxy through Next.js API
      apiKey: process.env.NEXT_PUBLIC_NATUREOS_API_KEY
    });
    
    client.listDevices().then(setDevices);
  }, []);
  
  return <div>{/* Render devices */}</div>;
}
```

## Cross-Platform Data Flow

### Example: End-to-End Workflow

1. **Device → NatureOS**: MycoBrain device sends sensor data
2. **NatureOS → NLM**: NLM ingests data via NatureOS API
3. **NLM Processing**: NLM processes data and updates knowledge graph
4. **NLM → MAS**: MAS agent queries NLM for recommendations
5. **MAS → NatureOS**: MAS sends command via SDK to adjust device
6. **Website Display**: Website shows device status and NLM insights

```python
# Complete workflow example
from natureos_sdk import NatureOSClient
from nlm import NLMClient
from mycosoft_mas.integrations import UnifiedIntegrationManager

# Initialize clients
natureos = NatureOSClient(...)
nlm = NLMClient(...)
mas = UnifiedIntegrationManager()

# 1. Get device data
data = await natureos.get_sensor_data(device_id="mycobrain-001")

# 2. Process with NLM
insights = await nlm.process_environmental_data(
    temperature=data[0].value,
    humidity=data[1].value
)

# 3. Get recommendations
recommendations = await nlm.recommend(
    scenario="optimal_growth",
    constraints={"device_id": "mycobrain-001"}
)

# 4. Execute via MAS agent
if recommendations.action == "increase_humidity":
    await natureos.send_command(
        device_id="mycobrain-001",
        command_type="set_mosfet",
        parameters={"channel": 3, "state": "on"}
    )
```

## Authentication & Security

### API Keys

Each integration requires API keys:

```bash
# NLM
NLM_API_KEY=your_nlm_api_key

# NatureOS
NATUREOS_API_KEY=your_natureos_api_key
NATUREOS_TENANT_ID=your_tenant_id

# MAS
MAS_API_KEY=your_mas_api_key

# Website
WEBSITE_API_KEY=your_website_api_key
```

### Authentication Flow

1. Client authenticates with API key
2. Server validates API key
3. Server checks tenant permissions (if applicable)
4. Server processes request
5. Server returns response

## Error Handling

All integrations implement consistent error handling:

```python
from natureos_sdk import NatureOSError
from nlm import NLMError

try:
    result = await client.get_device(device_id="esp32-001")
except NatureOSError as e:
    if e.status_code == 404:
        # Device not found
        pass
    elif e.status_code == 401:
        # Authentication failed
        pass
    else:
        # Other error
        pass
```

## Monitoring & Logging

All integrations support monitoring:

- **Health Checks**: `/health` endpoints
- **Metrics**: Prometheus metrics
- **Logging**: Structured JSON logging
- **Tracing**: Correlation IDs for request tracking

## Best Practices

1. **Use Connection Pooling**: Reuse HTTP clients
2. **Implement Retry Logic**: Handle transient failures
3. **Cache When Possible**: Reduce API calls
4. **Monitor Rate Limits**: Respect API limits
5. **Handle Errors Gracefully**: Provide fallbacks
6. **Use Async/Await**: Non-blocking operations
7. **Validate Input**: Check data before sending
8. **Log Operations**: Track integration activity

## Troubleshooting

### Common Issues

1. **Connection Timeout**: Increase timeout or check network
2. **Authentication Failed**: Verify API keys
3. **Rate Limit Exceeded**: Implement backoff
4. **Data Sync Issues**: Check sync logs
5. **Missing Data**: Verify integration state

### Debug Mode

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# SDK debug
client = NatureOSClient(..., debug=True)

# NLM debug
nlm = NLMClient(..., debug=True)
```

