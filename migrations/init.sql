-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS financial;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS security;

-- Create core tables
CREATE TABLE IF NOT EXISTS core.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'inactive',
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, type)
);

CREATE TABLE IF NOT EXISTS core.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID REFERENCES core.agents(id),
    receiver_id UUID REFERENCES core.agents(id),
    type VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create financial tables
CREATE TABLE IF NOT EXISTS financial.transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES core.agents(id),
    type VARCHAR(100) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create monitoring tables
CREATE TABLE IF NOT EXISTS monitoring.metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES core.agents(id),
    name VARCHAR(255) NOT NULL,
    value DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (agent_id, name, timestamp)
);

CREATE TABLE IF NOT EXISTS monitoring.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES core.agents(id),
    type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create security tables
CREATE TABLE IF NOT EXISTS security.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(100) NOT NULL,
    key_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (service, key_hash)
);

CREATE TABLE IF NOT EXISTS security.rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    max_requests INTEGER NOT NULL,
    time_window INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (service, endpoint)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agents_type ON core.agents(type);
CREATE INDEX IF NOT EXISTS idx_messages_status ON core.messages(status);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON financial.transactions(status);
CREATE INDEX IF NOT EXISTS idx_metrics_agent_id ON monitoring.metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON monitoring.alerts(status);
CREATE INDEX IF NOT EXISTS idx_api_keys_service ON security.api_keys(service);

-- Create trigger function for updating timestamps
CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $func$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$func$ LANGUAGE plpgsql;

-- Create trigger for agents table
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON core.agents
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Create trigger for rate_limits table
CREATE TRIGGER update_rate_limits_updated_at
    BEFORE UPDATE ON security.rate_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp(); 