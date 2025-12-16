-- =============================================================================
-- ACTION AUDIT LOG SCHEMA
-- =============================================================================
-- This schema supports the action audit logging and approval gates feature.
-- Tables are created in the 'audit' schema for organization.

-- Create audit schema
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO audit, public;

-- =============================================================================
-- ACTION AUDIT LOG TABLE
-- =============================================================================
-- Stores all tool/action executions with full audit trail

CREATE TABLE IF NOT EXISTS audit.action_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identifiers
    correlation_id UUID NOT NULL,
    agent_run_id UUID,
    agent_id VARCHAR(255) NOT NULL,
    
    -- Action details
    action_type VARCHAR(100) NOT NULL,
    action_name VARCHAR(255) NOT NULL,
    action_category VARCHAR(100),
    
    -- Inputs/Outputs (redacted sensitive data)
    inputs JSONB,
    outputs JSONB,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    error_type VARCHAR(100),
    
    -- Approval tracking
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_status VARCHAR(50),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Metadata
    metadata JSONB,
    request_metadata JSONB,
    
    -- Indexes for common queries
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'rejected', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT valid_approval_status CHECK (approval_status IS NULL OR approval_status IN ('pending', 'approved', 'rejected', 'auto_approved'))
);

-- =============================================================================
-- APPROVAL POLICIES TABLE
-- =============================================================================
-- Configures which actions require approval and under what conditions

CREATE TABLE IF NOT EXISTS audit.approval_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Policy identification
    policy_name VARCHAR(255) NOT NULL UNIQUE,
    policy_description TEXT,
    
    -- Matching criteria
    action_category VARCHAR(100),
    action_type VARCHAR(100),
    action_name_pattern VARCHAR(255),
    agent_id_pattern VARCHAR(255),
    
    -- Policy rules
    requires_approval BOOLEAN DEFAULT TRUE,
    auto_approve_conditions JSONB,
    
    -- Approval workflow
    min_approvers INTEGER DEFAULT 1,
    approval_timeout_minutes INTEGER DEFAULT 60,
    escalation_after_minutes INTEGER,
    escalation_to VARCHAR(255),
    
    -- Risk classification
    risk_level VARCHAR(50) DEFAULT 'medium',
    
    -- Policy status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    CONSTRAINT valid_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- =============================================================================
-- AGENT RUN LOG TABLE
-- =============================================================================
-- Tracks agent execution runs for correlation

CREATE TABLE IF NOT EXISTS audit.agent_run_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Run identification
    run_id UUID NOT NULL UNIQUE,
    correlation_id UUID NOT NULL,
    parent_run_id UUID REFERENCES audit.agent_run_log(run_id),
    
    -- Agent details
    agent_id VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100),
    
    -- Task details
    task_type VARCHAR(100),
    task_description TEXT,
    task_input JSONB,
    task_output JSONB,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    error_message TEXT,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Metrics
    actions_count INTEGER DEFAULT 0,
    llm_calls_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 6),
    
    -- Metadata
    metadata JSONB,
    
    CONSTRAINT valid_run_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- =============================================================================
-- LLM CALL LOG TABLE
-- =============================================================================
-- Tracks LLM API calls for audit and cost tracking

CREATE TABLE IF NOT EXISTS audit.llm_call_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identifiers
    correlation_id UUID NOT NULL,
    agent_run_id UUID REFERENCES audit.agent_run_log(run_id),
    agent_id VARCHAR(255),
    
    -- Provider details
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(255) NOT NULL,
    
    -- Request
    request_type VARCHAR(50) NOT NULL,
    messages JSONB,
    parameters JSONB,
    
    -- Response
    response JSONB,
    finish_reason VARCHAR(50),
    
    -- Usage metrics
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    
    -- Cost tracking
    estimated_cost DECIMAL(10, 6),
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_message TEXT,
    
    CONSTRAINT valid_request_type CHECK (request_type IN ('chat', 'completion', 'embedding', 'function_call')),
    CONSTRAINT valid_llm_status CHECK (status IN ('success', 'failed', 'timeout', 'rate_limited'))
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Action audit log indexes
CREATE INDEX IF NOT EXISTS idx_action_audit_correlation ON audit.action_audit_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_action_audit_agent_run ON audit.action_audit_log(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_action_audit_agent ON audit.action_audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_action_audit_status ON audit.action_audit_log(status);
CREATE INDEX IF NOT EXISTS idx_action_audit_created ON audit.action_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_audit_category ON audit.action_audit_log(action_category);
CREATE INDEX IF NOT EXISTS idx_action_audit_requires_approval ON audit.action_audit_log(requires_approval) WHERE requires_approval = TRUE;

-- Approval policies indexes
CREATE INDEX IF NOT EXISTS idx_approval_policies_active ON audit.approval_policies(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_approval_policies_category ON audit.approval_policies(action_category);

-- Agent run log indexes
CREATE INDEX IF NOT EXISTS idx_agent_run_correlation ON audit.agent_run_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_run_agent ON audit.agent_run_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_run_status ON audit.agent_run_log(status);
CREATE INDEX IF NOT EXISTS idx_agent_run_created ON audit.agent_run_log(created_at DESC);

-- LLM call log indexes
CREATE INDEX IF NOT EXISTS idx_llm_call_correlation ON audit.llm_call_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_agent_run ON audit.llm_call_log(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_provider ON audit.llm_call_log(provider);
CREATE INDEX IF NOT EXISTS idx_llm_call_model ON audit.llm_call_log(model);
CREATE INDEX IF NOT EXISTS idx_llm_call_created ON audit.llm_call_log(created_at DESC);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION audit.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_approval_policies_modtime
    BEFORE UPDATE ON audit.approval_policies
    FOR EACH ROW
    EXECUTE FUNCTION audit.update_updated_at();

-- =============================================================================
-- DEFAULT APPROVAL POLICIES
-- =============================================================================

INSERT INTO audit.approval_policies (
    policy_name,
    policy_description,
    action_category,
    requires_approval,
    risk_level,
    priority
) VALUES 
    ('external_write_approval', 'Require approval for external write operations', 'external_write', TRUE, 'high', 100),
    ('financial_approval', 'Require approval for financial operations', 'financial', TRUE, 'critical', 90),
    ('data_deletion_approval', 'Require approval for data deletion', 'data_deletion', TRUE, 'high', 95),
    ('system_config_approval', 'Require approval for system configuration changes', 'system_config', TRUE, 'critical', 85),
    ('read_operations_auto', 'Auto-approve read operations', 'read', FALSE, 'low', 200)
ON CONFLICT (policy_name) DO NOTHING;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Recent actions view
CREATE OR REPLACE VIEW audit.recent_actions AS
SELECT 
    aal.id,
    aal.correlation_id,
    aal.agent_id,
    aal.action_name,
    aal.action_category,
    aal.status,
    aal.requires_approval,
    aal.approval_status,
    aal.created_at,
    aal.duration_ms,
    arl.task_type
FROM audit.action_audit_log aal
LEFT JOIN audit.agent_run_log arl ON aal.agent_run_id = arl.run_id
ORDER BY aal.created_at DESC
LIMIT 1000;

-- Pending approvals view
CREATE OR REPLACE VIEW audit.pending_approvals AS
SELECT 
    id,
    correlation_id,
    agent_id,
    action_name,
    action_category,
    inputs,
    created_at,
    metadata
FROM audit.action_audit_log
WHERE requires_approval = TRUE 
  AND approval_status = 'pending'
ORDER BY created_at ASC;

-- LLM usage summary view
CREATE OR REPLACE VIEW audit.llm_usage_summary AS
SELECT 
    DATE(created_at) as date,
    provider,
    model,
    COUNT(*) as call_count,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost) as total_cost,
    AVG(duration_ms) as avg_duration_ms
FROM audit.llm_call_log
WHERE status = 'success'
GROUP BY DATE(created_at), provider, model
ORDER BY date DESC, total_cost DESC;
