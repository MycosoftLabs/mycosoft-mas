# MYCA MAS Upgrade Summary

This document summarizes the upgrades made to MYCA MAS for local Docker deployment, multi-model LLM support, and operational standards.

## Overview

The upgrade adds:
1. **Local-first Docker runtime** with one-command startup
2. **Multi-model LLM abstraction layer** supporting OpenAI, Gemini, and local models
3. **Operational standards** (health/ready endpoints, metrics, structured logging)
4. **Agent safety** (audit logs, approval gates)
5. **Integration standardization** (typed clients for external APIs)

All changes are **backwards compatible** and **non-destructive**.

## Files Added/Changed

### Docker & Infrastructure

- **`docker-compose.local.yml`** - Enhanced local development compose file
  - All services with healthchecks
  - LiteLLM proxy for unified LLM access
  - Proper dependency ordering
  - Persistent volumes

- **`Makefile`** - Convenience commands
  - `make up` - Start all services
  - `make down` - Stop services
  - `make logs` - View logs
  - `make health` / `make ready` - Check endpoints
  - `make reset-db` - Reset database
  - `make test` / `make fmt` / `make lint` - Development commands

- **`config/litellm_config.yaml`** - LiteLLM proxy configuration
  - Model list with fallbacks
  - Rate limiting and caching
  - Support for OpenAI, Anthropic, Gemini, local models

### LLM Abstraction Layer

- **`mycosoft_mas/llm/`** - New LLM module
  - `providers.py` - Provider implementations (OpenAI, Gemini, OpenAI-compatible)
  - `router.py` - LLM router with fallback support
  - `registry.py` - Model registry and configuration
  - `__init__.py` - Module exports

- **`config/models.yaml`** - Model registry configuration
  - Model roles (planning, execution, fast, embedding, fallback)
  - Provider configurations
  - Selection policies

### Core Enhancements

- **`mycosoft_mas/core/myca_main.py`** - Updated
  - Added `/ready` endpoint for readiness checks
  - Checks PostgreSQL, Redis, Qdrant connectivity

- **`mycosoft_mas/core/audit.py`** - New audit logging system
  - Action audit logs in PostgreSQL
  - Approval gates for risky actions
  - Correlation ID tracking
  - Sensitive data redaction

- **`mycosoft_mas/core/logging_config.py`** - New structured logging
  - JSON log formatting
  - Correlation ID support
  - Context-aware logging
  - Secret redaction

### Integration Clients

- **`mycosoft_mas/integrations/clients/`** - New integration clients
  - `base_client.py` - Base client with retry logic
  - `mindex_client.py` - MINDEX API client
  - `natureos_client.py` - NatureOS API client
  - `website_client.py` - Website API client

### Documentation

- **`docs/LOCAL_DEV.md`** - Comprehensive local development guide
  - Setup instructions
  - Service URLs
  - LLM configuration options
  - Troubleshooting

- **`.env.example`** - Environment variable template
  - All required variables documented
  - Sensible defaults for local development

## How to Run Locally

### Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your API keys (optional for local LLM)

# 3. Start everything
make up

# 4. Verify
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

### Service URLs

- **MAS API**: http://localhost:8001
- **Health**: http://localhost:8001/health
- **Ready**: http://localhost:8001/ready
- **Metrics**: http://localhost:8001/metrics
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **LiteLLM**: http://localhost:4000
- **Qdrant**: http://localhost:6333

## LLM Configuration

### Option 1: Local LLM (via LiteLLM)

```bash
# In .env
LLM_BASE_URL=http://localhost:4000
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_MODEL_PLANNING=local-llm
```

Configure LiteLLM in `config/litellm_config.yaml` to point to your local model server.

### Option 2: Remote Providers

```bash
# OpenAI
OPENAI_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_PROVIDER=openai

# Or via LiteLLM (unified)
LLM_BASE_URL=http://localhost:4000
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

### Option 3: Model Selection

Edit `config/models.yaml` to configure:
- Model roles (planning, execution, fast, embedding)
- Provider mappings
- Fallback chains

## Using the LLM Router

```python
from mycosoft_mas.llm import LLMRouter, ModelRole

router = LLMRouter()

# Use planning model
response = await router.chat(
    messages=[{"role": "user", "content": "Plan a task"}],
    role=ModelRole.PLANNING,
)

# Use execution model
response = await router.chat(
    messages=[{"role": "user", "content": "Execute task"}],
    role=ModelRole.EXECUTION,
)

# Generate embeddings
embedding = await router.embed("text to embed")
```

## Audit Logging

Actions are automatically logged to `audit.action_logs` table:

```python
from mycosoft_mas.core.audit import get_audit_logger, ActionCategory

audit_logger = get_audit_logger()

# Log an action
action_id = await audit_logger.log_action(
    agent_id="agent-1",
    agent_name="MyAgent",
    action_type="tool_call",
    category=ActionCategory.EXTERNAL_WRITE,
    inputs={"tool": "send_email", "to": "user@example.com"},
    tool_name="send_email",
)

# Update on completion
await audit_logger.update_action(
    action_id,
    status=ActionStatus.COMPLETED,
    outputs={"result": "success"},
)
```

## Integration Clients

```python
from mycosoft_mas.integrations.clients import MINDEXClient, NatureOSClient

# MINDEX
async with MINDEXClient() as client:
    members = await client.get_data("members")
    project = await client.create_resource("projects", {"name": "New Project"})

# NatureOS
async with NatureOSClient() as client:
    entities = await client.get_entities("organisms")
```

## Environment Variables

Key variables (see `.env.example` for full list):

- **Database**: `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Redis**: `REDIS_URL`
- **Qdrant**: `QDRANT_URL`
- **LLM**: `LLM_BASE_URL`, `LLM_DEFAULT_PROVIDER`, `LLM_MODEL_*`
- **Providers**: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`
- **Audit**: `APPROVAL_REQUIRED`, `ACTION_AUDIT_ENABLED`

## Database Schema

New tables:
- `audit.action_logs` - Action audit trail

Existing tables unchanged (backwards compatible).

## Metrics

New Prometheus metrics:
- `llm_requests_total` - LLM request counts by provider/model/status
- `llm_request_duration_seconds` - LLM request latency
- `llm_tokens_total` - Token usage by provider/model/type

Existing metrics unchanged.

## Backwards Compatibility

✅ **All existing APIs work unchanged**
✅ **No breaking changes to agent interfaces**
✅ **Existing config files still work**
✅ **Database migrations are additive only**

## Next Steps

1. **Test locally**: `make up && make health`
2. **Configure LLM**: Edit `.env` and `config/models.yaml`
3. **Review audit logs**: Check `audit.action_logs` table
4. **Explore integrations**: Use client stubs in `integrations/clients/`

## Troubleshooting

See `docs/LOCAL_DEV.md` for detailed troubleshooting guide.

Common issues:
- **Port conflicts**: Modify ports in `.env`
- **Database connection**: Check `DATABASE_URL` format
- **LLM errors**: Check LiteLLM logs: `docker compose logs litellm-proxy`
- **Service health**: Use `make ready` to check dependencies

## Validation Checklist

- [x] `make up` brings up all services
- [x] `/health` returns OK
- [x] `/ready` returns OK after dependencies are ready
- [x] LLM router can call OpenAI
- [x] LLM router can call Gemini (if key set)
- [x] LLM router can call local endpoint (if configured)
- [x] Metrics include LLM counters
- [x] Actions logged to audit table
- [x] No secrets committed

## Files Summary

**Added:**
- `docker-compose.local.yml`
- `Makefile`
- `config/litellm_config.yaml`
- `config/models.yaml`
- `mycosoft_mas/llm/` (entire module)
- `mycosoft_mas/core/audit.py`
- `mycosoft_mas/core/logging_config.py`
- `mycosoft_mas/integrations/clients/` (entire module)
- `docs/LOCAL_DEV.md`
- `.env.example`
- `UPGRADE_SUMMARY.md` (this file)

**Modified:**
- `mycosoft_mas/core/myca_main.py` (added `/ready` endpoint)

**Unchanged:**
- All existing agent code
- All existing service code
- All existing API routes
- Database schema (additive only)
