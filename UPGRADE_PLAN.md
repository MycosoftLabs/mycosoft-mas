# MYCA MAS Upgrade Plan - Local Docker + Multi-Model Runtime

## Overview
This document outlines the incremental, backwards-compatible upgrade plan for MYCA MAS to support full local Docker deployment with multi-model LLM capabilities.

## Current State Analysis

### ✅ Existing (Working)
- Docker Compose with Postgres, Redis, Qdrant, Prometheus, Grafana
- Basic health endpoints (`/health`, `/metrics`)
- FastAPI-based MAS orchestrator
- Multiple specialized agents (Mycology, Financial, Corporate, etc.)
- Basic Prometheus metrics
- Agent-based architecture with messaging

### ⚠️ Gaps Identified
1. **No LLM provider abstraction** - Direct OpenAI/Anthropic usage if any
2. **No local LLM support** - No LiteLLM/vLLM/Ollama integration
3. **No readiness endpoint** - Only liveness health check
4. **No structured logging** - Basic Python logging without correlation IDs
5. **No action audit trail** - No typed tool actions or approval gates
6. **Limited metrics** - Missing LLM call tracking, tool execution metrics
7. **Config fragmentation** - Multiple config files without validation
8. **No Makefile** - Manual docker compose commands
9. **Missing documentation** - No LOCAL_DEV.md with setup steps

## Implementation Phases

### Phase 1: Docker Foundation (Priority 1)
**Goal**: Stable local-first runtime with one-command startup

#### 1.1 Enhanced Docker Compose
- [x] Review existing `docker-compose.yml`
- [ ] Add LiteLLM proxy service (OpenAI-compatible endpoint)
- [ ] Add optional Ollama profile for local models
- [ ] Fix healthchecks and dependencies
- [ ] Add persistent volumes for all stateful services
- [ ] Configure proper networking

#### 1.2 Makefile for Operations
- [ ] Create `Makefile` with:
  - `make up` - Start all services
  - `make down` - Stop all services
  - `make logs` - Follow logs
  - `make health` - Check all services
  - `make reset-db` - Reset databases
  - `make test` - Run tests
  - `make fmt` - Format code

#### 1.3 Environment Configuration
- [ ] Create comprehensive `.env.example`
- [ ] Document all environment variables
- [ ] Add validation at startup

**Deliverables**:
- Enhanced `docker-compose.yml`
- `docker-compose.local.yml` (optional profiles)
- `Makefile`
- `.env.example`

---

### Phase 2: Multi-Model LLM Layer (Priority 1)
**Goal**: Provider-agnostic LLM abstraction with routing

#### 2.1 LLM Module Structure
Create `mycosoft_mas/llm/` with:
- `provider.py` - Base provider interface
- `openai_provider.py` - OpenAI + Azure OpenAI
- `gemini_provider.py` - Google Gemini
- `openai_compatible_provider.py` - LiteLLM/vLLM/Ollama
- `router.py` - Model selection and fallback logic
- `registry.py` - Model configuration
- `config.py` - LLM-specific config

#### 2.2 Model Configuration
Create `config/models.yaml`:
```yaml
models:
  planning:
    provider: openai
    model: gpt-4-turbo-preview
    temperature: 0.7
  execution:
    provider: openai_compatible
    model: llama-3-70b
    base_url: http://litellm:4000
  fast:
    provider: openai
    model: gpt-3.5-turbo
  embedding:
    provider: openai
    model: text-embedding-3-small

providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
  gemini:
    api_key: ${GEMINI_API_KEY}
  openai_compatible:
    api_key: ${LOCAL_LLM_API_KEY:-dummy}
    base_url: ${LOCAL_LLM_BASE_URL:-http://litellm:4000}

routing:
  strategy: task_type  # task_type, cost, latency
  fallback_enabled: true
  fallback_chain:
    - openai
    - openai_compatible
```

#### 2.3 Integration with Agents
- [ ] Update BaseAgent to use LLMRouter
- [ ] Add LLM call tracking to metrics
- [ ] Add retry logic and error handling
- [ ] Support streaming responses

**Deliverables**:
- `mycosoft_mas/llm/` module (7 files)
- `config/models.yaml`
- Updated `BaseAgent` with LLM integration

---

### Phase 3: Operational Standards (Priority 2)
**Goal**: Production-grade observability and reliability

#### 3.1 Health & Readiness
- [ ] Add `/ready` endpoint (checks DB, Redis, Qdrant connectivity)
- [ ] Enhance `/health` with service dependencies
- [ ] Add health checks for all Docker services
- [ ] Implement startup probes with retries

#### 3.2 Structured Logging
- [ ] Add JSON formatter for logs
- [ ] Implement correlation ID middleware
- [ ] Add request/response logging
- [ ] Secret redaction in logs
- [ ] Configure log levels per environment

#### 3.3 Enhanced Metrics
Add new Prometheus metrics:
```python
llm_calls_total{provider, model, status}
llm_call_duration_seconds{provider, model}
llm_tokens_total{provider, model, type}  # type=prompt/completion
tool_executions_total{tool_name, status}
tool_duration_seconds{tool_name}
agent_runs_total{agent_name, status}
agent_run_duration_seconds{agent_name}
action_audit_logs_total{action_type, status}
```

#### 3.4 Standardized Config
- [ ] Create `mycosoft_mas/config/` module
- [ ] Single config loader with validation
- [ ] Environment variable override support
- [ ] Config printing at startup (sanitized)
- [ ] Pydantic models for config validation

**Deliverables**:
- `/ready` endpoint
- Structured logging with correlation IDs
- Enhanced Prometheus metrics
- Config validation system

---

### Phase 4: Agent Safety & Audit (Priority 2)
**Goal**: Typed actions, audit logging, approval gates

#### 4.1 Typed Tool Actions
Create `mycosoft_mas/actions/`:
- `base_action.py` - BaseAction with Pydantic
- `file_actions.py` - File read/write/delete
- `api_actions.py` - External API calls
- `db_actions.py` - Database operations
- `integration_actions.py` - MINDEX/NatureOS calls

#### 4.2 Action Audit Log
Database schema:
```sql
CREATE TABLE action_audit_logs (
    id UUID PRIMARY KEY,
    correlation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    agent_run_id VARCHAR(64),
    action_type VARCHAR(128) NOT NULL,
    action_category VARCHAR(64),  -- read, write, external, risky
    inputs JSONB,  -- redacted
    outputs JSONB,  -- redacted
    status VARCHAR(32),  -- pending, approved, rejected, executed, failed
    error TEXT,
    approved_by VARCHAR(64),
    approval_required BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP,
    duration_ms INTEGER
);

CREATE INDEX idx_action_audit_correlation ON action_audit_logs(correlation_id);
CREATE INDEX idx_action_audit_agent ON action_audit_logs(agent_id);
CREATE INDEX idx_action_audit_status ON action_audit_logs(status);
```

#### 4.3 Approval Gates
- [ ] Configurable approval policy (`APPROVAL_REQUIRED=true/false`)
- [ ] Action category classification
- [ ] Approval flow (manual/auto based on category)
- [ ] Audit trail for approvals

**Deliverables**:
- `mycosoft_mas/actions/` module
- Database migration for audit logs
- Approval gate implementation
- Action execution middleware

---

### Phase 5: Integration Standardization (Priority 3)
**Goal**: Clean, typed integration clients

#### 5.1 Clients Module
Create `mycosoft_mas/clients/`:
- `base_client.py` - Base client with retry, auth, typing
- `mindex_client.py` - MINDEX API client
- `natureos_client.py` - NatureOS API client
- `website_client.py` - Website API client

#### 5.2 Contracts
- [ ] Create `contracts/` folder with OpenAPI schemas
- [ ] Pin contract versions
- [ ] Generate Pydantic models from schemas
- [ ] Version compatibility checks

**Deliverables**:
- `mycosoft_mas/clients/` module
- `contracts/` with OpenAPI specs
- Type-safe integration clients

---

### Phase 6: Testing & Documentation (Priority 3)
**Goal**: Validated, documented system

#### 6.1 Tests
- [ ] Unit tests for LLM router/providers
- [ ] Integration test: Docker Compose boot
- [ ] Integration test: Health/ready endpoints
- [ ] Integration test: Trivial agent run
- [ ] Integration test: LLM call via LiteLLM
- [ ] CI workflow for tests

#### 6.2 Documentation
- [ ] `docs/LOCAL_DEV.md` - Complete setup guide
- [ ] `docs/MULTI_MODEL_LLM.md` - LLM configuration guide
- [ ] `docs/ACTION_AUDIT.md` - Action logging guide
- [ ] Update main `README.md`

**Deliverables**:
- Test suite covering new functionality
- Complete documentation
- CI integration

---

## Implementation Order

### Week 1: Docker Foundation + LLM Layer
1. Day 1-2: Enhanced Docker Compose + Makefile
2. Day 3-5: LLM provider abstraction + LiteLLM integration

### Week 2: Observability + Safety
1. Day 1-2: Health/readiness + structured logging
2. Day 3-5: Enhanced metrics + action audit logging

### Week 3: Integration + Polish
1. Day 1-2: Integration clients + contracts
2. Day 3-4: Tests + documentation
3. Day 5: Final validation + PR

---

## Backwards Compatibility Strategy

### Rules
1. **No breaking API changes** - All existing endpoints remain functional
2. **Additive only** - New modules, no rewrites
3. **Optional features** - New functionality can be disabled via config
4. **Gradual migration** - Agents can adopt new LLM layer incrementally

### Safety Measures
- All changes in feature branches
- Comprehensive testing before merge
- Rollback plan for each phase
- Config flags for new features

---

## Risk Mitigation

### Risk: Docker networking issues
**Mitigation**: Test on clean Docker environment, provide troubleshooting guide

### Risk: LLM provider API changes
**Mitigation**: Provider abstraction isolates changes, comprehensive error handling

### Risk: Performance degradation from audit logging
**Mitigation**: Async logging, batched writes, retention policies

### Risk: Config complexity
**Mitigation**: Sensible defaults, validation with clear errors, documentation

---

## Success Metrics

- [ ] `make up` brings up all services reliably (5/5 attempts)
- [ ] `/health` returns 200 within 60s of startup
- [ ] `/ready` returns 200 after dependencies are up
- [ ] Agent can execute trivial task locally
- [ ] LLM calls work with 3 providers (OpenAI, Gemini, local)
- [ ] Metrics include LLM/tool/action counters
- [ ] Action audit logs persisted with correlation IDs
- [ ] Zero secrets in Git
- [ ] Documentation allows new developer to run locally in <30min

---

## Files to Create/Modify

### New Files (40+)
```
mycosoft_mas/llm/__init__.py
mycosoft_mas/llm/provider.py
mycosoft_mas/llm/openai_provider.py
mycosoft_mas/llm/gemini_provider.py
mycosoft_mas/llm/openai_compatible_provider.py
mycosoft_mas/llm/router.py
mycosoft_mas/llm/registry.py
mycosoft_mas/llm/config.py

mycosoft_mas/actions/__init__.py
mycosoft_mas/actions/base_action.py
mycosoft_mas/actions/file_actions.py
mycosoft_mas/actions/api_actions.py
mycosoft_mas/actions/db_actions.py
mycosoft_mas/actions/integration_actions.py

mycosoft_mas/clients/__init__.py
mycosoft_mas/clients/base_client.py
mycosoft_mas/clients/mindex_client.py
mycosoft_mas/clients/natureos_client.py

mycosoft_mas/core/logging.py
mycosoft_mas/core/correlation.py
mycosoft_mas/core/readiness.py

config/models.yaml
.env.example
Makefile
docker-compose.local.yml

migrations/002_action_audit_logs.sql

tests/llm/test_router.py
tests/llm/test_providers.py
tests/integration/test_docker_compose.py
tests/integration/test_health_endpoints.py

docs/LOCAL_DEV.md
docs/MULTI_MODEL_LLM.md
docs/ACTION_AUDIT.md
```

### Modified Files (10+)
```
docker-compose.yml
mycosoft_mas/agents/base_agent.py
mycosoft_mas/core/myca_main.py
mycosoft_mas/orchestrator.py (if exists)
config/settings.py
requirements.txt
pyproject.toml
README.md
.gitignore
```

---

## Next Steps

1. ✅ Create this plan
2. Get approval/feedback
3. Start Phase 1: Docker Foundation
4. Implement incrementally with PRs per phase
5. Test thoroughly at each step
6. Document as we go

---

## Notes

- This is a **non-destructive upgrade** - all existing functionality remains intact
- Implementation is **incremental** - each phase can be merged independently
- All changes are **backwards compatible**
- Docker is the **source of truth** for local development
- **Secrets hygiene** is mandatory - no commits of secrets ever
