# MAS Integration Modules

This directory contains integration clients for external systems used by the Mycosoft Multi-Agent System.

## Overview

The MAS integrates with multiple external systems to provide comprehensive functionality:

1. **MINDEX** - Mycological Index Database (PostgreSQL/PostGIS)
2. **NATUREOS** - Cloud IoT platform for device management
3. **Website** - Mycosoft website API (Vercel deployment)
4. **Notion** - Knowledge management and documentation
5. **N8N** - Workflow automation platform

## Architecture

Each integration is implemented as a standalone client module with:
- Async HTTP client for API communication
- Database connection pooling (for MINDEX)
- Error handling and retry logic
- Health check capabilities
- Context manager support for resource cleanup

The `UnifiedIntegrationManager` provides a single interface for all integrations.

## Quick Start

### Basic Usage

```python
from mycosoft_mas.integrations import UnifiedIntegrationManager

# Initialize manager
manager = UnifiedIntegrationManager()
await manager.initialize()

# Access individual clients
taxa = await manager.mindex.get_taxa(limit=10)
devices = await manager.natureos.list_devices()

# Check health of all systems
health = await manager.check_all_health()

# Clean up
await manager.close()
```

### Using Individual Clients

```python
from mycosoft_mas.integrations import MINDEXClient, NotionClient

# MINDEX client
async with MINDEXClient() as mindex:
    taxa = await mindex.get_taxa(limit=10)
    observations = await mindex.get_observations(bbox=[-180, -90, 180, 90])

# Notion client
async with NotionClient() as notion:
    pages = await notion.query_database(database_id="abc123")
    page = await notion.create_page(
        database_id="abc123",
        properties={"Title": {"title": [{"text": {"content": "New Page"}}]}}
    )
```

## Configuration

### Environment Variables

Each integration can be configured via environment variables:

#### MINDEX
```bash
MINDEX_DATABASE_URL=postgresql://mindex:mindex@localhost:5432/mindex
MINDEX_API_URL=http://localhost:8000
MINDEX_API_KEY=your_api_key  # Optional
```

#### NATUREOS
```bash
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_api_key
NATUREOS_TENANT_ID=your_tenant_id  # Optional
```

#### Website
```bash
WEBSITE_API_URL=https://mycosoft.vercel.app/api
WEBSITE_API_KEY=your_api_key  # Optional
```

#### Notion
```bash
NOTION_API_KEY=secret_xxx
NOTION_DATABASE_ID=abc123  # Optional default
```

#### N8N
```bash
N8N_WEBHOOK_URL=http://localhost:5678
N8N_API_URL=http://localhost:5678  # Optional, defaults to webhook URL
N8N_API_KEY=your_api_key  # Optional
```

### Configuration Dictionary

Alternatively, pass configuration when initializing:

```python
config = {
    "mindex": {
        "database_url": "postgresql://...",
        "api_url": "http://...",
        "timeout": 30
    },
    "notion": {
        "api_key": "secret_xxx",
        "database_id": "abc123"
    }
}

manager = UnifiedIntegrationManager(config=config)
```

## Integration Details

### MINDEX Client

**Purpose:** Access mycological database with taxonomy, observations, telemetry, and IP assets.

**Key Methods:**
- `get_taxa()` - Retrieve taxonomy records
- `get_observations()` - Get geospatial observation data
- `get_telemetry_latest()` - Latest device telemetry
- `get_ip_assets()` - IP asset catalog
- `anchor_ip_asset_hypergraph()` - Blockchain anchoring
- `bind_ip_asset_solana()` - Solana token binding

**Database:** PostgreSQL with PostGIS extension

**API:** REST API with optional API key authentication

### NATUREOS Client

**Purpose:** Manage IoT devices and collect sensor data.

**Key Methods:**
- `list_devices()` - List all registered devices
- `get_device()` - Get device details
- `get_sensor_data()` - Retrieve sensor readings
- `register_device()` - Register new device
- `update_device_config()` - Update device configuration

**API:** REST API with Bearer token authentication

### Website Client

**Purpose:** Interact with Mycosoft website API.

**Key Methods:**
- `get_content()` - Get website content
- `submit_contact_form()` - Submit contact forms
- `subscribe_newsletter()` - Newsletter subscriptions
- `get_analytics()` - Website analytics (requires API key)

**API:** REST API deployed on Vercel

### Notion Client

**Purpose:** Knowledge management, documentation, and logging.

**Key Methods:**
- `query_database()` - Query Notion databases
- `create_page()` - Create new pages
- `update_page()` - Update existing pages
- `append_blocks()` - Add content blocks
- `search()` - Search workspace

**API:** Notion API v1 with integration token

### N8N Client

**Purpose:** Workflow automation and event-driven actions.

**Key Methods:**
- `trigger_workflow()` - Trigger workflow via webhook
- `get_workflows()` - List all workflows (API)
- `execute_workflow()` - Execute workflow via API
- `get_executions()` - Get execution history

**Access:** Webhooks (public) and API (authenticated)

## Unified Integration Manager

The `UnifiedIntegrationManager` provides:

### Features
- Single initialization point for all integrations
- Unified health checking
- Coordinated operations
- Error handling and metrics
- Connection management

### Methods
- `initialize()` - Initialize all clients
- `check_all_health()` - Health check all systems
- `get_integration_status()` - Comprehensive status
- `sync_mindex_to_notion()` - Sync taxonomy to Notion
- `trigger_n8n_workflow_for_agent()` - Agent event workflows
- `log_to_notion()` - Agent activity logging
- `close()` - Clean up all connections

### Example: Coordinated Operations

```python
manager = UnifiedIntegrationManager()
await manager.initialize()

# Sync MINDEX data to Notion
await manager.sync_mindex_to_notion(
    database_id="notion_db_id",
    limit=100
)

# Trigger workflow on agent event
await manager.trigger_n8n_workflow_for_agent(
    workflow_id="webhook/agent-events",
    agent_id="agent_1",
    event_type="task_completed",
    data={"task_id": "task_123"}
)

# Log agent activity
await manager.log_to_notion(
    database_id="logs_db_id",
    title="Agent Task Completed",
    content="Agent completed task successfully",
    metadata={"agent_id": "agent_1", "task_id": "task_123"}
)
```

## Error Handling

All clients include comprehensive error handling:

- **HTTP Errors:** Caught and logged with context
- **Connection Errors:** Retry logic (configurable)
- **Timeout Errors:** Configurable timeouts
- **Authentication Errors:** Clear error messages

Example error handling:

```python
try:
    taxa = await manager.mindex.get_taxa(limit=10)
except httpx.HTTPError as e:
    logger.error(f"MINDEX API error: {e}")
    # Handle error
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle error
```

## Health Checks

All clients support health checks:

```python
# Individual client health
mindex_health = await manager.mindex.health_check()

# All systems health
all_health = await manager.check_all_health()

# Status includes:
# - status: "ok", "error", or "not_configured"
# - timestamp: Check timestamp
# - error: Error message (if status is "error")
```

## Best Practices

1. **Use Context Managers:** Always use `async with` for automatic cleanup
2. **Check Health:** Verify system availability before operations
3. **Handle Errors:** Implement proper error handling and retries
4. **Monitor Metrics:** Track request counts and errors
5. **Close Connections:** Always close clients when done

## Troubleshooting

### Connection Issues
- Verify environment variables are set correctly
- Check network connectivity to API endpoints
- Verify API keys and authentication credentials

### Database Issues (MINDEX)
- Ensure PostgreSQL is running and accessible
- Verify PostGIS extension is installed
- Check database credentials and permissions

### API Issues
- Check API endpoint URLs
- Verify API keys are valid
- Review API rate limits

## Testing

Each client can be tested independently:

```python
# Test MINDEX
async def test_mindex():
    async with MINDEXClient() as client:
        health = await client.health_check()
        assert health["api_status"] == "ok"
        taxa = await client.get_taxa(limit=1)
        assert len(taxa) > 0

# Test unified manager
async def test_unified_manager():
    async with UnifiedIntegrationManager() as manager:
        health = await manager.check_all_health()
        assert "MINDEX" in health
```

## Documentation

For detailed API documentation, see:
- [MINDEX Client](mindex_client.py) - Full docstring documentation
- [NATUREOS Client](natureos_client.py) - Full docstring documentation
- [Website Client](website_client.py) - Full docstring documentation
- [Notion Client](notion_client.py) - Full docstring documentation
- [N8N Client](n8n_client.py) - Full docstring documentation
- [Unified Manager](unified_integration_manager.py) - Full docstring documentation

## Support

For issues or questions:
1. Check individual client docstrings
2. Review environment variable configuration
3. Check system health status
4. Review error logs

## License

Part of the Mycosoft Multi-Agent System.
