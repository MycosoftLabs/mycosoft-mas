# SDK Database Schema

This document describes the database schema used by the NatureOS SDK for local caching, state management, and advanced features.

## Overview

The SDK can optionally use a local database for:
- Caching device and sensor data
- Offline operation support
- Local state management
- Advanced querying capabilities

## Supported Databases

- **PostgreSQL**: Full feature support
- **SQLite**: Lightweight local development
- **Redis**: Caching layer (optional)

## Schema

### `sdk.cache`

Caching layer for device and sensor data.

```sql
CREATE SCHEMA IF NOT EXISTS sdk;

CREATE TABLE IF NOT EXISTS sdk.device_cache (
    device_id VARCHAR(255) PRIMARY KEY,
    device_data JSONB NOT NULL,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    ttl_seconds INTEGER DEFAULT 3600
);

CREATE INDEX idx_device_cache_expires ON sdk.device_cache(expires_at);

CREATE TABLE IF NOT EXISTS sdk.sensor_data_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    sensor_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    value DECIMAL(10, 4),
    unit VARCHAR(50),
    metadata JSONB,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, sensor_type, timestamp)
);

CREATE INDEX idx_sensor_cache_device ON sdk.sensor_data_cache(device_id);
CREATE INDEX idx_sensor_cache_type ON sdk.sensor_data_cache(sensor_type);
CREATE INDEX idx_sensor_cache_timestamp ON sdk.sensor_data_cache(timestamp DESC);
CREATE INDEX idx_sensor_cache_device_type ON sdk.sensor_data_cache(device_id, sensor_type);
```

### `sdk.state`

Local state management for SDK operations.

```sql
CREATE TABLE IF NOT EXISTS sdk.state (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sdk.command_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    command_type VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'completed', 'failed'
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_command_queue_device ON sdk.command_queue(device_id);
CREATE INDEX idx_command_queue_status ON sdk.command_queue(status);
CREATE INDEX idx_command_queue_created ON sdk.command_queue(created_at DESC);
```

### `sdk.analytics`

Local analytics and metrics storage.

```sql
CREATE TABLE IF NOT EXISTS sdk.analytics.api_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    request_size INTEGER,
    response_size INTEGER,
    error_message TEXT,
    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_calls_endpoint ON sdk.analytics.api_calls(endpoint);
CREATE INDEX idx_api_calls_status ON sdk.analytics.api_calls(status_code);
CREATE INDEX idx_api_calls_called ON sdk.analytics.api_calls(called_at DESC);

CREATE TABLE IF NOT EXISTS sdk.analytics.device_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value DECIMAL(10, 4),
    metadata JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_metrics_device ON sdk.analytics.device_metrics(device_id);
CREATE INDEX idx_device_metrics_type ON sdk.analytics.device_metrics(metric_type);
CREATE INDEX idx_device_metrics_recorded ON sdk.analytics.device_metrics(recorded_at DESC);
```

## SQLite Schema (Lightweight)

For SQLite, use a simplified schema:

```sql
CREATE TABLE IF NOT EXISTS device_cache (
    device_id TEXT PRIMARY KEY,
    device_data TEXT NOT NULL, -- JSON string
    cached_at INTEGER NOT NULL, -- Unix timestamp
    expires_at INTEGER,
    ttl_seconds INTEGER DEFAULT 3600
);

CREATE INDEX idx_device_cache_expires ON device_cache(expires_at);

CREATE TABLE IF NOT EXISTS sensor_data_cache (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL, -- Unix timestamp
    value REAL,
    unit TEXT,
    metadata TEXT, -- JSON string
    cached_at INTEGER NOT NULL,
    UNIQUE(device_id, sensor_type, timestamp)
);

CREATE INDEX idx_sensor_cache_device ON sensor_data_cache(device_id);
CREATE INDEX idx_sensor_cache_timestamp ON sensor_data_cache(timestamp DESC);
```

## Redis Schema (Caching)

For Redis caching, use the following key patterns:

```
# Device cache
device:{device_id} -> JSON string
device:{device_id}:ttl -> expiration timestamp

# Sensor data cache
sensor:{device_id}:{sensor_type}:{timestamp} -> JSON string
sensor:{device_id}:{sensor_type}:latest -> latest reading

# Command queue
command:queue:{device_id} -> List of command IDs
command:{command_id} -> JSON string

# State
state:{key} -> JSON string
```

## Usage

### Enable Database Caching

```python
from natureos_sdk import NatureOSClient
from natureos_sdk.database import DatabaseCache

# Initialize with database cache
cache = DatabaseCache(
    database_url="postgresql://user:pass@localhost:5432/sdk"
)

client = NatureOSClient(
    api_url="http://localhost:8002",
    api_key="your_api_key",
    cache=cache
)
```

### Offline Mode

```python
from natureos_sdk import NatureOSClient
from natureos_sdk.database import OfflineMode

# Enable offline mode
client = NatureOSClient(
    api_url="http://localhost:8002",
    api_key="your_api_key",
    offline_mode=True,
    database_url="sqlite:///sdk_cache.db"
)

# Will use cached data when offline
devices = await client.list_devices()  # Uses cache if API unavailable
```

## Migration

The SDK automatically creates the schema on first use. For manual migration:

```python
from natureos_sdk.database import migrate_schema

await migrate_schema(database_url="postgresql://...")
```

