# System Integration Documentation

## Overview

The Mycosoft Multi-Agent System (MAS) integrates with four core systems plus supporting platforms:

1. **MINDEX** - Mycological Index Database (PostgreSQL/PostGIS)
2. **NATUREOS** - Cloud IoT Platform
3. **Website** - Mycosoft Website (Vercel)
4. **MAS** - Multi-Agent System (this system)
5. **Notion** - Knowledge Management
6. **N8N** - Workflow Automation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MAS Orchestrator                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Agent   │  │ Agent   │  │ Agent   │  │ Agent   │  ...    │
│  │Manager │  │Manager │  │Manager │  │Manager │          │
│  └────┬───┘  └────┬───┘  └────┬───┘  └────┬───┘          │
└───────┼──────────┼──────────┼──────────┼──────────────────────┘
        │          │          │          │
        └──────────┼──────────┼──────────┘
                  │          │
        ┌──────────┴──────────┐
        │  Unified Integration Manager                          │
        └──────────────────────────────────────────────────────────────┐
    ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │ MINDEX │ NATUREOS │ Website │ Notion │ N8N  │
    └──────┴──────────┴──────────┴──────────┴──────────┘
```

## Integration Flow

### Data Flow

1. **MAS → MINDEX**: Agents query taxonomy, observations, IP assets
2. **MAS → NATUREOS**: Device management, sensor data collection
3. **MAS → Website**: Content updates, form submissions, analytics
4. **MAS → Notion**: Documentation, logging, knowledge base
5. **MAS → N8N**: Workflow triggers, automation

### Event Flow

1. **Agent Events → N8N**: Task completion, errors, status changes
2. **N8N → Notion**: Logging workflows
3. **N8N → Website**: Content updates, notifications
4. **Website → NATUREOS**: Device registration events

## MINDEX Integration

### Purpose
- Store and query mycological taxonomy data
- Track observations with geospatial data
- Manage IP assets with blockchain bindings
- Store telemetry data

### Connection
- **Database**: PostgreSQL with PostGIS
- **API**: REST API at `MINDEX_API_URL`
- **Authentication**: Optional API key

### Data Types
- **Taxonomy**: Species, genera, families
- **Observations**: Geospatial observation records
- **Telemetry**: Device sensor data
- **IP Assets**: Intellectual property with blockchain anchors

### Usage in MAS
```python
from mycosoft_mas.integrations import UnifiedIntegrationManager

manager = UnifiedIntegrationManager()
await manager.initialize()

# Query taxonomy
taxa = await manager.mindex.get_taxa(limit=10, scientific_name="Agaricus")

# Get observations in bounding box
obs = await manager.mindex.get_observations(bbox=[-122.5, 37.7, -122.3, 37.8])

# Get IP assets
assets = await manager.mindex.get_ip_assets(limit=25)
```

## NATUREOS Integration

### Purpose
- Manage IoT devices (ESP32, Raspberry Pi)
- Collect sensor data
- Monitor device status
- Configure devices remotely

### Connection
- **API**: REST API at `NATUREOS_API_URL`
- **Authentication**: Bearer token

### Data Types
- **Devices**: Device registry and status
- **Sensor Data**: Temperature, humidity, CO2, etc.
- **Configurations**: Device settings

### Usage in MAS
```python
# List devices
devices = await manager.natureos.list_devices(device_type="esp32", status="online")

# Get sensor data
data = await manager.natureos.get_sensor_data(
    device_id="esp32-001",
    sensor_type="temperature",
    start_time=start,
    end_time=end
)

# Register device
device = await manager.natureos.register_device(
    device_id="esp32-002",
    name="Field Sensor 2",
    device_type="esp32",
    location={"lat": 37.7749, "lon": -122.4194}
)
```

## Website Integration

### Purpose
- Update website content
- Submit forms
- Track analytics
- Newsletter management

### Connection
- **API**: REST API at `WEBSITE_API_URL` (Vercel)
- **Authentication**: Optional API key

### Usage in MAS
```python
# Get content
content = await manager.website.get_content(page="about")

# Submit contact form
result = await manager.website.submit_contact_form(
    name="John Doe",
    email="john@example.com",
    message="Inquiry about products"
)

# Get analytics
analytics = await manager.website.get_analytics(start_date=start, end_date=end)
```

## Notion Integration

### Purpose
- Documentation management
- Knowledge base
- Agent activity logging
- Project tracking

### Connection
- **API**: Notion API v1
- **Authentication**: Integration token

### Usage in MAS
```python
# Query database
pages = await manager.notion.query_database(
    database_id="abc123",
    filter_properties={"Status": {"equals": "Active"}
)

# Create page
page = await manager.notion.create_page(
    database_id="abc123",
    properties={
        "Title": {"title": [{"text": {"content": "Agent Log"}}],
        "Content": {"rich_text": [{"text": {"content": "Agent completed task"}}
    }
)

# Log agent activity
await manager.log_to_notion(
        database_id="logs_db",
        title="Task Completed",
        content="Agent completed task successfully",
        metadata={"agent_id": "agent_1", "task_id": "task_123"}
    )
```

## N8N Integration

### Purpose
- Workflow automation
- Event-driven actions
- Task orchestration
- Notifications

### Connection
- **Webhooks**: Public webhook URLs
- **API**: Authenticated API (optional)

### Usage in MAS
```python
# Trigger workflow on agent event
await manager.trigger_n8n_workflow_for_agent(
    workflow_id="webhook/agent-events",
    agent_id="agent_1",
    event_type="task_completed",
    data={"task_id": "task_123", "result": "success"}
)

# Get workflows
workflows = await manager.n8n.get_workflows()

# Get execution history
executions = await manager.n8n.get_executions(workflow_id="abc123")
```

## Unified Operations

### Cross-System Workflows

#### 1. MINDEX → Notion Sync
```python
# Sync taxonomy to Notion knowledge base
await manager.sync_mindex_to_notion(
    database_id="taxonomy_db",
    limit=100
)
```

#### 2. Agent Events → N8N → Notion
```python
# Agent event triggers workflow, workflow logs to Notion
await manager.trigger_n8n_workflow_for_agent(
    workflow_id="webhook/agent-events",
    agent_id="agent_1",
    event_type="task_completed",
    data={"task_id": "task_123"}
)
```

#### 3. NATUREOS → MINDEX → Notion
```python
# Device data → MINDEX telemetry → Notion logs
device_data = await manager.natureos.get_sensor_data("esp32-001")
# Store in MINDEX
# Log to Notion
await manager.log_to_notion(
    database_id="device_logs",
    title=f"Device {device_id} Data",
    content=json.dumps(device_data)
)
```

## Configuration

### Environment Variables

See [integrations/README.md](../mycosoft_mas/integrations/README.md) for complete environment variable documentation.

### Docker Compose

Integration URLs are configured in `docker-compose.yml`:

```yaml
environment:
  - MINDEX_DATABASE_URL=postgresql://mindex:mindex@host.docker.internal:5432/mindex
  - MINDEX_API_URL=http://host.docker.internal:8000
  - NATUREOS_API_URL=http://host.docker.internal:8002
  - WEBSITE_API_URL=https://mycosoft.vercel.app/api
  - NOTION_API_KEY=secret_xxx
  - NOTION_DATABASE_ID=abc123
  - N8N_WEBHOOK_URL=http://host.docker.internal:5678
```

### Config File

Integration settings in `config.yaml`:

```yaml
integrations:
  mindex:
    database_url: ${MINDEX_DATABASE_URL}
    api_url: ${MINDEX_API_URL}
    timeout: 30
  natureos:
    api_url: ${NATUREOS_API_URL}
    api_key: ${NATUREOS_API_KEY}
  website:
    api_url: ${WEBSITE_API_URL}
  notion:
    api_key: ${NOTION_API_KEY}
    database_id: ${NOTION_DATABASE_ID}
  n8n:
    webhook_url: ${N8N_WEBHOOK_URL}
    api_url: ${N8N_API_URL}
    api_key: ${N8N_API_KEY}
```

## Health Monitoring

### Health Checks

All integrations support health checks:

```python
# Individual
mindex_health = await manager.mindex.health_check()
natureos_health = await manager.natureos.health_check()

# All systems
all_health = await manager.check_all_health()
```

### Status Endpoint

```python
status = await manager.get_integration_status()
# Returns:
# {
#   "initialized": true,
#   "health": {
#     "MINDEX": {"status": "ok", ...},
#     "NATUREOS": {"status": "ok", ...},
#     ...
#   },
#   "metrics": {...},
#   "last_health_check": "..."
# }
```

## Error Handling

### Retry Logic
- Automatic retries on transient errors
- Exponential backoff
- Circuit breaker pattern

### Error Types
- **Connection Errors**: Network issues, timeouts
- **Authentication Errors**: Invalid credentials
- **API Errors**: HTTP errors, rate limits
- **Database Errors**: Connection failures, query errors

## Performance

### Connection Pooling
- MINDEX: PostgreSQL connection pool (2-10 connections)
- HTTP clients: Reused connections

### Caching
- Health check results cached (5 minutes)
- Query results cached where applicable

### Rate Limiting
- Respects API rate limits
- Automatic backoff on rate limit errors

## Security

### Authentication
- API keys stored in environment variables
- Bearer tokens for NATUREOS
- Notion integration tokens

### Data Protection
- Encrypted connections (HTTPS)
- Secure credential storage
- Access control

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check network connectivity
   - Verify API endpoints
   - Check authentication credentials

2. **Database Connection**
   - Verify PostgreSQL is running
   - Check database credentials
   - Verify PostGIS extension

3. **API Errors**
   - Check API keys
   - Verify rate limits
   - Review error responses

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check health status:

```python
health = await manager.check_all_health()
for system, status in health.items():
    print(f"{system}: {status['status']}")
```

## Future Enhancements

1. **Real-time Sync**: WebSocket connections for real-time updates
2. **Batch Operations**: Bulk data operations
3. **Advanced Filtering**: Complex query builders
4. **Webhook Support**: Event-driven integrations
5. **Metrics Dashboard**: Integration performance metrics

## References

- [MINDEX GitHub](https://github.com/MycosoftLabs/mindex)
- [NATUREOS GitHub](https://github.com/MycosoftLabs/NatureOS)
- [Website GitHub](https://github.com/MycosoftLabs/website)
- [Notion API Docs](https://developers.notion.com/)
- [N8N Docs](https://docs.n8n.io/)

