# NLM Database Schema

This document describes the PostgreSQL database schema for the Nature Learning Model (NLM).

## Overview

NLM uses PostgreSQL with the following extensions:
- `uuid-ossp`: UUID generation
- `pg_trgm`: Text similarity search
- `hstore`: Key-value storage
- `PostGIS`: Geospatial data (optional, for location-based queries)

## Schemas

### `nlm.core`
Core model and training data.

### `nlm.knowledge`
Knowledge graph storage.

### `nlm.predictions`
Prediction history and results.

### `nlm.integrations`
Integration state and synchronization.

## Tables

### `nlm.core.models`

Stores trained model artifacts and metadata.

```sql
CREATE SCHEMA IF NOT EXISTS nlm;
CREATE SCHEMA IF NOT EXISTS nlm.core;
CREATE SCHEMA IF NOT EXISTS nlm.knowledge;
CREATE SCHEMA IF NOT EXISTS nlm.predictions;
CREATE SCHEMA IF NOT EXISTS nlm.integrations;

CREATE TABLE IF NOT EXISTS nlm.core.models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL UNIQUE,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL, -- 'base', 'fine-tuned', 'specialized'
    architecture JSONB NOT NULL,
    training_config JSONB,
    training_data_hash VARCHAR(64),
    model_path TEXT NOT NULL,
    metrics JSONB, -- Training metrics, validation scores
    status VARCHAR(50) NOT NULL DEFAULT 'training', -- 'training', 'ready', 'deprecated'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

CREATE INDEX idx_models_status ON nlm.core.models(status);
CREATE INDEX idx_models_type ON nlm.core.models(model_type);
CREATE INDEX idx_models_version ON nlm.core.models(model_version);
```

### `nlm.core.training_runs`

Tracks training runs and experiments.

```sql
CREATE TABLE IF NOT EXISTS nlm.core.training_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES nlm.core.models(id),
    run_name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    dataset_path TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed', 'cancelled'
    metrics JSONB, -- Loss, accuracy, etc. over time
    error_message TEXT,
    created_by VARCHAR(255)
);

CREATE INDEX idx_training_runs_model ON nlm.core.training_runs(model_id);
CREATE INDEX idx_training_runs_status ON nlm.core.training_runs(status);
CREATE INDEX idx_training_runs_started ON nlm.core.training_runs(started_at DESC);
```

### `nlm.knowledge.entities`

Knowledge graph entities (species, locations, conditions, etc.).

```sql
CREATE TABLE IF NOT EXISTS nlm.knowledge.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL, -- 'species', 'location', 'condition', 'observation'
    entity_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    properties JSONB NOT NULL DEFAULT '{}',
    embedding VECTOR(768), -- Vector embedding for semantic search
    metadata JSONB,
    source VARCHAR(255), -- 'mindex', 'natureos', 'manual', 'inferred'
    confidence DECIMAL(3,2), -- 0.00 to 1.00
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX idx_entities_type ON nlm.knowledge.entities(entity_type);
CREATE INDEX idx_entities_id ON nlm.knowledge.entities(entity_id);
CREATE INDEX idx_entities_embedding ON nlm.knowledge.entities USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_entities_source ON nlm.knowledge.entities(source);
```

### `nlm.knowledge.relations`

Relationships between entities in the knowledge graph.

```sql
CREATE TABLE IF NOT EXISTS nlm.knowledge.relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id UUID REFERENCES nlm.knowledge.entities(id),
    target_entity_id UUID REFERENCES nlm.knowledge.entities(id),
    relation_type VARCHAR(100) NOT NULL, -- 'thrives_in', 'requires', 'inhibits', 'correlates_with'
    strength DECIMAL(3,2), -- Relationship strength 0.00 to 1.00
    properties JSONB,
    metadata JSONB,
    source VARCHAR(255),
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_relations_source ON nlm.knowledge.relations(source_entity_id);
CREATE INDEX idx_relations_target ON nlm.knowledge.relations(target_entity_id);
CREATE INDEX idx_relations_type ON nlm.knowledge.relations(relation_type);
```

### `nlm.knowledge.observations`

Structured observations that feed into the knowledge graph.

```sql
CREATE TABLE IF NOT EXISTS nlm.knowledge.observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    observation_type VARCHAR(100) NOT NULL, -- 'environmental', 'biological', 'temporal'
    entity_id UUID REFERENCES nlm.knowledge.entities(id),
    data JSONB NOT NULL,
    location JSONB, -- {lat, lon, elevation}
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_device_id VARCHAR(255),
    source_system VARCHAR(100), -- 'natureos', 'mindex', 'manual'
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_observations_type ON nlm.knowledge.observations(observation_type);
CREATE INDEX idx_observations_entity ON nlm.knowledge.observations(entity_id);
CREATE INDEX idx_observations_timestamp ON nlm.knowledge.observations(timestamp DESC);
CREATE INDEX idx_observations_source ON nlm.knowledge.observations(source_system);
CREATE INDEX idx_observations_processed ON nlm.knowledge.observations(processed);
```

### `nlm.predictions.predictions`

Stores prediction requests and results.

```sql
CREATE TABLE IF NOT EXISTS nlm.predictions.predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_type VARCHAR(100) NOT NULL, -- 'species_growth', 'environmental', 'temporal'
    entity_id UUID REFERENCES nlm.knowledge.entities(id),
    model_id UUID REFERENCES nlm.core.models(id),
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    confidence DECIMAL(3,2),
    time_horizon VARCHAR(50), -- '1d', '7d', '30d', '1y'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_predictions_type ON nlm.predictions.predictions(prediction_type);
CREATE INDEX idx_predictions_entity ON nlm.predictions.predictions(entity_id);
CREATE INDEX idx_predictions_model ON nlm.predictions.predictions(model_id);
CREATE INDEX idx_predictions_status ON nlm.predictions.predictions(status);
CREATE INDEX idx_predictions_created ON nlm.predictions.predictions(created_at DESC);
```

### `nlm.predictions.prediction_accuracy`

Tracks prediction accuracy over time for model evaluation.

```sql
CREATE TABLE IF NOT EXISTS nlm.predictions.prediction_accuracy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID REFERENCES nlm.predictions.predictions(id),
    actual_value JSONB,
    predicted_value JSONB,
    error_metrics JSONB, -- MAE, RMSE, etc.
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prediction_accuracy_prediction ON nlm.predictions.prediction_accuracy(prediction_id);
CREATE INDEX idx_prediction_accuracy_evaluated ON nlm.predictions.prediction_accuracy(evaluated_at DESC);
```

### `nlm.integrations.integration_state`

Tracks integration state and synchronization.

```sql
CREATE TABLE IF NOT EXISTS nlm.integrations.integration_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_name VARCHAR(100) NOT NULL, -- 'natureos', 'mindex', 'mas', 'website'
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50) NOT NULL DEFAULT 'idle', -- 'idle', 'syncing', 'error'
    sync_config JSONB,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(integration_name)
);

CREATE INDEX idx_integration_state_name ON nlm.integrations.integration_state(integration_name);
CREATE INDEX idx_integration_state_status ON nlm.integrations.integration_state(sync_status);
```

### `nlm.integrations.sync_log`

Logs synchronization events.

```sql
CREATE TABLE IF NOT EXISTS nlm.integrations.sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_name VARCHAR(100) NOT NULL,
    sync_type VARCHAR(100) NOT NULL, -- 'full', 'incremental', 'manual'
    records_processed INTEGER DEFAULT 0,
    records_succeeded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_sync_log_integration ON nlm.integrations.sync_log(integration_name);
CREATE INDEX idx_sync_log_status ON nlm.integrations.sync_log(status);
CREATE INDEX idx_sync_log_started ON nlm.integrations.sync_log(started_at DESC);
```

## Triggers

### Auto-update timestamps

```sql
CREATE OR REPLACE FUNCTION nlm.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_models_modtime
    BEFORE UPDATE ON nlm.core.models
    FOR EACH ROW
    EXECUTE FUNCTION nlm.update_updated_at_column();

CREATE TRIGGER update_entities_modtime
    BEFORE UPDATE ON nlm.knowledge.entities
    FOR EACH ROW
    EXECUTE FUNCTION nlm.update_updated_at_column();

CREATE TRIGGER update_relations_modtime
    BEFORE UPDATE ON nlm.knowledge.relations
    FOR EACH ROW
    EXECUTE FUNCTION nlm.update_updated_at_column();

CREATE TRIGGER update_integration_state_modtime
    BEFORE UPDATE ON nlm.integrations.integration_state
    FOR EACH ROW
    EXECUTE FUNCTION nlm.update_updated_at_column();
```

## Views

### `nlm.knowledge.entity_summary`

Summary view of entities with relation counts.

```sql
CREATE OR REPLACE VIEW nlm.knowledge.entity_summary AS
SELECT 
    e.id,
    e.entity_type,
    e.entity_id,
    e.name,
    e.description,
    e.confidence,
    e.source,
    COUNT(DISTINCT r1.id) as outgoing_relations,
    COUNT(DISTINCT r2.id) as incoming_relations,
    COUNT(DISTINCT o.id) as observation_count,
    e.created_at,
    e.updated_at
FROM nlm.knowledge.entities e
LEFT JOIN nlm.knowledge.relations r1 ON e.id = r1.source_entity_id
LEFT JOIN nlm.knowledge.relations r2 ON e.id = r2.target_entity_id
LEFT JOIN nlm.knowledge.observations o ON e.id = o.entity_id
GROUP BY e.id, e.entity_type, e.entity_id, e.name, e.description, 
         e.confidence, e.source, e.created_at, e.updated_at;
```

## Initialization Script

See `migrations/init_nlm_schema.sql` for the complete initialization script.

## Migration

Use Alembic for database migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Initial NLM schema"

# Apply migration
alembic upgrade head
```

