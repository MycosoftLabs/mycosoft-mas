-- Migration: Action Audit Logs
-- Create audit logging tables for agent actions
-- Author: MYCA MAS Upgrade
-- Date: 2025-12-16

-- ============================================================================
-- Action Audit Logs Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS action_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Correlation and tracing
    correlation_id VARCHAR(64) NOT NULL,
    trace_id VARCHAR(64),
    parent_span_id VARCHAR(64),
    
    -- Agent context
    agent_id VARCHAR(64) NOT NULL,
    agent_name VARCHAR(128),
    agent_run_id VARCHAR(64),
    
    -- Action details
    action_type VARCHAR(128) NOT NULL,
    action_category VARCHAR(64) NOT NULL,  -- read, write, external, risky, database
    action_name VARCHAR(256),
    
    -- Inputs and outputs (redacted)
    inputs JSONB,
    outputs JSONB,
    
    -- Status and execution
    status VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, executing, completed, failed
    error_type VARCHAR(128),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Approval workflow
    approval_required BOOLEAN DEFAULT false,
    approved_by VARCHAR(64),
    approval_timestamp TIMESTAMP,
    approval_notes TEXT,
    
    -- Timing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Additional metadata
    metadata JSONB,
    tags VARCHAR(128)[],
    
    -- Audit trail
    created_by VARCHAR(64),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX idx_action_audit_correlation ON action_audit_logs(correlation_id);
CREATE INDEX idx_action_audit_agent ON action_audit_logs(agent_id);
CREATE INDEX idx_action_audit_status ON action_audit_logs(status);
CREATE INDEX idx_action_audit_created_at ON action_audit_logs(created_at DESC);
CREATE INDEX idx_action_audit_category ON action_audit_logs(action_category);
CREATE INDEX idx_action_audit_type ON action_audit_logs(action_type);
CREATE INDEX idx_action_audit_run ON action_audit_logs(agent_run_id);

-- GIN index for JSONB columns
CREATE INDEX idx_action_audit_inputs_gin ON action_audit_logs USING gin(inputs);
CREATE INDEX idx_action_audit_metadata_gin ON action_audit_logs USING gin(metadata);

-- Composite indexes for common queries
CREATE INDEX idx_action_audit_agent_status ON action_audit_logs(agent_id, status, created_at DESC);
CREATE INDEX idx_action_audit_category_status ON action_audit_logs(action_category, status, created_at DESC);

-- ============================================================================
-- Action Categories Enum (for validation)
-- ============================================================================
CREATE TYPE action_category_type AS ENUM (
    'read',              -- Safe read operations
    'write',             -- File/data write operations
    'external',          -- External API calls
    'risky',             -- Potentially dangerous operations
    'database',          -- Database modifications
    'integration',       -- Integration service calls
    'agent_control',     -- Agent lifecycle management
    'system'             -- System-level operations
);

-- Add check constraint for category
ALTER TABLE action_audit_logs 
    ADD CONSTRAINT check_action_category 
    CHECK (action_category IN ('read', 'write', 'external', 'risky', 'database', 'integration', 'agent_control', 'system'));

-- Add check constraint for status
ALTER TABLE action_audit_logs 
    ADD CONSTRAINT check_action_status 
    CHECK (status IN ('pending', 'approved', 'rejected', 'executing', 'completed', 'failed', 'cancelled'));

-- ============================================================================
-- Agent Run Logs Table (for run-level tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_run_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Run identification
    run_id VARCHAR(64) NOT NULL UNIQUE,
    correlation_id VARCHAR(64) NOT NULL,
    
    -- Agent context
    agent_id VARCHAR(64) NOT NULL,
    agent_name VARCHAR(128),
    
    -- Run details
    task_type VARCHAR(128),
    task_description TEXT,
    
    -- Status and results
    status VARCHAR(32) NOT NULL DEFAULT 'running',  -- running, completed, failed, cancelled
    result JSONB,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Statistics
    actions_total INTEGER DEFAULT 0,
    actions_successful INTEGER DEFAULT 0,
    actions_failed INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 4) DEFAULT 0.0,
    
    -- Metadata
    metadata JSONB,
    tags VARCHAR(128)[],
    
    -- Audit
    created_by VARCHAR(64),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_run_logs
CREATE INDEX idx_agent_run_correlation ON agent_run_logs(correlation_id);
CREATE INDEX idx_agent_run_agent ON agent_run_logs(agent_id);
CREATE INDEX idx_agent_run_status ON agent_run_logs(status);
CREATE INDEX idx_agent_run_started_at ON agent_run_logs(started_at DESC);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- Recent audit logs with run context
CREATE OR REPLACE VIEW recent_action_audits AS
SELECT 
    aal.*,
    arl.task_type,
    arl.task_description,
    arl.run_id AS run_context
FROM action_audit_logs aal
LEFT JOIN agent_run_logs arl ON aal.agent_run_id = arl.run_id
ORDER BY aal.created_at DESC
LIMIT 1000;

-- Action statistics by agent
CREATE OR REPLACE VIEW action_stats_by_agent AS
SELECT 
    agent_id,
    agent_name,
    COUNT(*) AS total_actions,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_actions,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_actions,
    COUNT(*) FILTER (WHERE approval_required = true) AS actions_requiring_approval,
    AVG(duration_ms) AS avg_duration_ms,
    MAX(created_at) AS last_action_at
FROM action_audit_logs
GROUP BY agent_id, agent_name;

-- Actions requiring approval
CREATE OR REPLACE VIEW pending_approvals AS
SELECT 
    aal.*,
    arl.task_description,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - aal.created_at)) AS pending_seconds
FROM action_audit_logs aal
LEFT JOIN agent_run_logs arl ON aal.agent_run_id = arl.run_id
WHERE aal.status = 'pending' 
  AND aal.approval_required = true
ORDER BY aal.created_at ASC;

-- ============================================================================
-- Functions for Audit Operations
-- ============================================================================

-- Function to create an action audit log
CREATE OR REPLACE FUNCTION log_action(
    p_correlation_id VARCHAR,
    p_agent_id VARCHAR,
    p_action_type VARCHAR,
    p_action_category VARCHAR,
    p_inputs JSONB DEFAULT NULL,
    p_approval_required BOOLEAN DEFAULT FALSE,
    p_metadata JSONB DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO action_audit_logs (
        correlation_id,
        agent_id,
        action_type,
        action_category,
        inputs,
        approval_required,
        metadata,
        status
    ) VALUES (
        p_correlation_id,
        p_agent_id,
        p_action_type,
        p_action_category,
        p_inputs,
        p_approval_required,
        p_metadata,
        CASE WHEN p_approval_required THEN 'pending' ELSE 'executing' END
    )
    RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update action status
CREATE OR REPLACE FUNCTION update_action_status(
    p_log_id UUID,
    p_status VARCHAR,
    p_outputs JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_duration_ms INTEGER DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE action_audit_logs SET
        status = p_status,
        outputs = COALESCE(p_outputs, outputs),
        error_message = COALESCE(p_error_message, error_message),
        duration_ms = COALESCE(p_duration_ms, duration_ms),
        completed_at = CASE WHEN p_status IN ('completed', 'failed', 'cancelled') THEN CURRENT_TIMESTAMP ELSE completed_at END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function to approve an action
CREATE OR REPLACE FUNCTION approve_action(
    p_log_id UUID,
    p_approved_by VARCHAR,
    p_approval_notes TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE action_audit_logs SET
        status = 'approved',
        approved_by = p_approved_by,
        approval_timestamp = CURRENT_TIMESTAMP,
        approval_notes = p_approval_notes,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_log_id
      AND status = 'pending'
      AND approval_required = true;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Triggers for Automatic Updates
-- ============================================================================

-- Trigger to automatically calculate duration
CREATE OR REPLACE FUNCTION calculate_action_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_ms := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at)) * 1000;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_action_duration
    BEFORE UPDATE ON action_audit_logs
    FOR EACH ROW
    WHEN (OLD.completed_at IS NULL AND NEW.completed_at IS NOT NULL)
    EXECUTE FUNCTION calculate_action_duration();

-- Trigger to update agent_run_logs statistics
CREATE OR REPLACE FUNCTION update_run_statistics()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.agent_run_id IS NOT NULL THEN
        UPDATE agent_run_logs SET
            actions_total = (
                SELECT COUNT(*) 
                FROM action_audit_logs 
                WHERE agent_run_id = NEW.agent_run_id
            ),
            actions_successful = (
                SELECT COUNT(*) 
                FROM action_audit_logs 
                WHERE agent_run_id = NEW.agent_run_id 
                  AND status = 'completed'
            ),
            actions_failed = (
                SELECT COUNT(*) 
                FROM action_audit_logs 
                WHERE agent_run_id = NEW.agent_run_id 
                  AND status = 'failed'
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE run_id = NEW.agent_run_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_run_statistics
    AFTER INSERT OR UPDATE ON action_audit_logs
    FOR EACH ROW
    WHEN (NEW.agent_run_id IS NOT NULL)
    EXECUTE FUNCTION update_run_statistics();

-- ============================================================================
-- Cleanup Policy (Retention)
-- ============================================================================

-- Function to clean up old audit logs (call periodically via cron)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM action_audit_logs
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL
      AND status IN ('completed', 'failed', 'cancelled');
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Data for Testing (Comment out in production)
-- ============================================================================

-- Uncomment to insert sample data for testing
-- INSERT INTO agent_run_logs (run_id, correlation_id, agent_id, agent_name, task_type) VALUES
-- ('run-001', 'corr-001', 'mycology-agent', 'MycologyBioAgent', 'research');

-- INSERT INTO action_audit_logs (correlation_id, agent_id, action_type, action_category, inputs, status) VALUES
-- ('corr-001', 'mycology-agent', 'research.query', 'read', '{"query": "mushroom cultivation"}'::jsonb, 'completed');

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- To rollback: DROP TABLE action_audit_logs CASCADE; DROP TABLE agent_run_logs CASCADE;
