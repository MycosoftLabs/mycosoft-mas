-- MYCA Integration Fabric - Postgres Initialization

CREATE TABLE IF NOT EXISTS myca_audit (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    request_id VARCHAR(255) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    integration VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(100),
    params_hash VARCHAR(64),
    response_hash VARCHAR(64),
    status VARCHAR(50) NOT NULL,
    duration_ms INTEGER,
    error_message TEXT,
    risk_level VARCHAR(50),
    confirmed BOOLEAN DEFAULT FALSE,
    correlation_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_myca_audit_timestamp ON myca_audit(timestamp DESC);
CREATE INDEX idx_myca_audit_request_id ON myca_audit(request_id);
CREATE INDEX idx_myca_audit_actor ON myca_audit(actor);
CREATE INDEX idx_myca_audit_integration ON myca_audit(integration);
CREATE INDEX idx_myca_audit_status ON myca_audit(status);

CREATE TABLE IF NOT EXISTS myca_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    source VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    correlation_id VARCHAR(255),
    data JSONB,
    handled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_myca_events_timestamp ON myca_events(timestamp DESC);
CREATE INDEX idx_myca_events_source ON myca_events(source);
CREATE INDEX idx_myca_events_severity ON myca_events(severity);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO n8n;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO n8n;
