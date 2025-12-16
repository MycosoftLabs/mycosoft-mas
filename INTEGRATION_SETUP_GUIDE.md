# Integration Setup Guide

## Quick Start

This guide helps you set up all integrations for the Mycosoft Multi-Agent System.

## Prerequisites

1. **MINDEX Database**: PostgreSQL with PostGIS extension
2. **NATUREOS**: Cloud platform running (or local instance)
3. **Website**: Deployed on Vercel (or local)
4. **Notion**: Workspace with integration created
5. **N8N**: Instance running (local or cloud)

## Step 1: Environment Variables

Create a `.env` file in the project root:

```bash
# MINDEX Configuration
MINDEX_DATABASE_URL=postgresql://mindex:mindex@localhost:5432/mindex
MINDEX_API_URL=http://localhost:8000
MINDEX_API_KEY=your_mindex_api_key  # Optional

# NATUREOS Configuration
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_natureos_api_key
NATUREOS_TENANT_ID=your_tenant_id  # Optional

# Website Configuration
WEBSITE_API_URL=https://mycosoft.vercel.app/api
WEBSITE_API_KEY=your_website_api_key  # Optional

# Notion Configuration
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=your_database_id  # Optional default

# N8N Configuration
N8N_WEBHOOK_URL=http://localhost:5678
N8N_API_URL=http://localhost:5678  # Optional
N8N_API_KEY=your_n8n_api_key  # Optional
```

## Step 2: Verify Connections

### Test MINDEX

```python
from mycosoft_mas.integrations import MINDEXClient

async with MINDEXClient() as client:
    health = await client.health_check()
    print(f"MINDEX Status: {health['api_status']}, DB: {health['database_status']}")
    
    # Test query
    taxa = await client.get_taxa(limit=5)
    print(f"Found {len(taxa)} taxa")
```

### Test NATUREOS

```python
from mycosoft_mas.integrations import NATUREOSClient

async with NATUREOSClient() as client:
    health = await client.health_check()
    print(f"NATUREOS Status: {health['status']}")
    
    # List devices
    devices = await client.list_devices()
    print(f"Found {len(devices)} devices")
```

### Test Website

```python
from mycosoft_mas.integrations import WebsiteClient

async with WebsiteClient() as client:
    health = await client.health_check()
    print(f"Website Status: {health['status']}")
```

### Test Notion

```python
from mycosoft_mas.integrations import NotionClient

async with NotionClient() as client:
    health = await client.health_check()
    print(f"Notion Status: {health['status']}")
    
    # Query database
    if client.default_database_id:
        pages = await client.query_database(database_id=client.default_database_id)
        print(f"Found {len(pages.get('results', []))} pages")
```

### Test N8N

```python
from mycosoft_mas.integrations import N8NClient

async with N8NClient() as client:
    health = await client.health_check()
    print(f"N8N Webhook: {health['webhook_status']}, API: {health['api_status']}")
```

## Step 3: Unified Manager

```python
from mycosoft_mas.integrations import UnifiedIntegrationManager

async with UnifiedIntegrationManager() as manager:
    # Check all systems
    health = await manager.check_all_health()
    for system, status in health.items():
        print(f"{system}: {status['status']}")
    
    # Use integrations
    taxa = await manager.mindex.get_taxa(limit=10)
    devices = await manager.natureos.list_devices()
    pages = await manager.notion.query_database(database_id="your_db_id")
```

## Step 4: Docker Configuration

Update `docker-compose.yml` environment variables are automatically passed to containers.

## Step 5: Verify Integration

Run the integration test:

```bash
python -m pytest tests/test_integrations.py -v
```

Or test manually:

```python
import asyncio
from mycosoft_mas.integrations import UnifiedIntegrationManager

async def test():
    async with UnifiedIntegrationManager() as manager:
        health = await manager.check_all_health()
        print("Integration Status:")
        for system, status in health.items():
            print(f"  {system}: {status['status']}")

asyncio.run(test())
```

## Troubleshooting

### MINDEX Connection Issues

1. **Database not accessible**
   ```bash
   # Check PostgreSQL is running
   psql -h localhost -U mindex -d mindex -c "SELECT 1"
   ```

2. **PostGIS not installed**
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

3. **API not responding**
   ```bash
   curl http://localhost:8000/health
   ```

### NATUREOS Connection Issues

1. **API not accessible**
   ```bash
   curl http://localhost:8002/health
   ```

2. **Authentication failed**
   - Verify API key is correct
   - Check token permissions

### Notion Connection Issues

1. **API key invalid**
   - Verify integration token in Notion settings
   - Check workspace permissions

2. **Database not found**
   - Verify database ID is correct
   - Check database exists in workspace

### N8N Connection Issues

1. **Webhook not accessible**
   ```bash
   curl http://localhost:5678/webhook/test
   ```

2. **API not accessible**
   - Verify N8N is running
   - Check API key if using authenticated endpoints

## Next Steps

1. Configure agents to use integrations
2. Set up automated workflows
3. Configure monitoring and alerts
4. Set up backups

## Support

For detailed documentation:
- [System Integrations](docs/SYSTEM_INTEGRATIONS.md)
- [Integration README](mycosoft_mas/integrations/README.md)

