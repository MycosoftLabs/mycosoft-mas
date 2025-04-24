-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS mas;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS tasks;
CREATE SCHEMA IF NOT EXISTS knowledge;

-- Set search path
SET search_path TO mas, agents, tasks, knowledge, public;

-- Create tables
CREATE TABLE IF NOT EXISTS agents.agent_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks.task_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL UNIQUE,
    agent_id VARCHAR(255) REFERENCES agents.agent_status(agent_id),
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 0,
    payload JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge.knowledge_nodes(id),
    target_id UUID REFERENCES knowledge.knowledge_nodes(id),
    relation_type VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agent_status_status ON agents.agent_status(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON tasks.task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_agent ON tasks.task_queue(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_type ON knowledge.knowledge_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_source ON knowledge.knowledge_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_target ON knowledge.knowledge_relations(target_id);

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_agent_status_modtime
    BEFORE UPDATE ON agents.agent_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_nodes_modtime
    BEFORE UPDATE ON knowledge.knowledge_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 