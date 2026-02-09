---
name: run-system-tests
description: Run comprehensive system tests across MAS, VMs, and APIs. Use when verifying system health, after deployments, or before releases.
---

# Run Comprehensive System Tests

## Quick Test (MAS Unit Tests)

```bash
cd /path/to/mycosoft-mas
poetry run pytest tests/ -v
```

## Full System Test Checklist

```
System Test Progress:
- [ ] Phase 1: Infrastructure (VMs and services)
- [ ] Phase 2: MAS API endpoints
- [ ] Phase 3: Memory system
- [ ] Phase 4: Agent registry
- [ ] Phase 5: Website health
- [ ] Phase 6: Integration tests
```

### Phase 1: Infrastructure

```bash
# Check all VMs are reachable
curl -s -o /dev/null -w "Sandbox: %{http_code}\n" http://192.168.0.187:3000
curl -s http://192.168.0.188:8001/health
curl -s http://192.168.0.189:8000/health
```

### Phase 2: MAS API Endpoints

```bash
# Core endpoints
curl -s http://192.168.0.188:8001/health
curl -s http://192.168.0.188:8001/version
curl -s http://192.168.0.188:8001/metrics

# Memory API
curl -s http://192.168.0.188:8001/api/memory/health

# Voice API
curl -s http://192.168.0.188:8001/voice/orchestrator/health
```

### Phase 3: Memory System

```bash
# Test memory write
curl -X POST http://192.168.0.188:8001/api/memory/write \
  -H "Content-Type: application/json" \
  -d '{"content": "test memory", "scope": "ephemeral", "source": "test"}'

# Test memory read
curl -s http://192.168.0.188:8001/api/memory/recent?limit=5
```

### Phase 4: Agent Registry

```bash
curl -s http://192.168.0.188:8001/api/registry/agents
curl -s http://192.168.0.188:8001/api/registry/agents/status
```

### Phase 5: Website Health

```bash
# Local dev
curl -s -o /dev/null -w "%{http_code}" http://localhost:3010

# Sandbox
curl -s -o /dev/null -w "%{http_code}" https://sandbox.mycosoft.com
```

### Phase 6: Integration Tests

```bash
poetry run pytest tests/ -v -k "integration"
```

## Automated Test Script

```bash
poetry run python scripts/comprehensive_test_suite.py
```

## Expected Results

- All health endpoints return 200 or JSON status "healthy"
- Unit tests pass with no failures
- Memory read/write operations succeed
- Agent registry returns registered agents
- Website responds on both dev and sandbox URLs
