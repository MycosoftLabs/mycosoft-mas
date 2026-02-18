# MAS Consciousness API Fix - February 12, 2026

## Problem

The test-voice page reported "MAS Consciousness: Error 404" when calling `/api/myca/status`.

```
[2026-02-12T17:53:09.546Z] [error] MAS Consciousness: Error 404
```

## Root Cause

The MAS VM's Python virtual environment was missing critical packages required by the `consciousness_api` router:

1. **`asyncpg`** - PostgreSQL async driver for database access
2. **`sse-starlette`** - Server-Sent Events support for streaming

When `consciousness_api.py` tried to import, it failed silently with `ModuleNotFoundError`. This caused `CONSCIOUSNESS_API_AVAILABLE = False` in `myca_main.py`, and the router was never registered - resulting in 404 for all `/api/myca/*` endpoints.

## Solution

### Step 1: Install Missing Packages

```bash
ssh mycosoft@192.168.0.188
cd /home/mycosoft/mycosoft/mas
./venv/bin/pip install asyncpg sse-starlette

# Or install all deps from pyproject.toml:
./venv/bin/pip install -e .
```

### Step 2: Verify Import Works

```bash
./venv/bin/python -c "from mycosoft_mas.core.routers.consciousness_api import router; print('SUCCESS')"
```

### Step 3: Restart Service

```bash
sudo systemctl restart mas-orchestrator
```

### Step 4: Verify Endpoint

```bash
curl http://localhost:8001/api/myca/ping
# Expected: {"status":"pong","message":"MYCA consciousness API is reachable"}
```

## Packages Installed

| Package | Version | Purpose |
|---------|---------|---------|
| asyncpg | 0.30.0 | PostgreSQL async driver |
| sse-starlette | 2.4.1 | Server-Sent Events |
| jinja2 | 3.1.6 | Template engine |
| python-multipart | 0.0.20 | Form data parsing |
| requests | 2.32.5 | HTTP client |
| MarkupSafe | 3.0.3 | String escaping |
| packaging | 24.2 | Version parsing |

## Verification

After fix:

```
GET /api/myca/ping
→ {"status":"pong","message":"MYCA consciousness API is reachable"}

GET /api/myca/status  
→ {"state":"dormant","is_conscious":false,"awake_since":null,...}

GET /health
→ {"status":"unhealthy","components":[{"name":"postgresql","status":"unhealthy",...}]}
```

Note: The health check still shows PostgreSQL as unhealthy (connection refused), but this is a separate issue from the consciousness API routing.

## Prevention

To prevent missing dependencies in the future:

1. Always run `pip install -e .` when deploying MAS
2. Add dependency check to deployment scripts
3. Consider using Docker with frozen dependencies

## Related Files

- `/home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/consciousness_api.py` - The router
- `/home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py` - Where router is registered
- `/etc/systemd/system/mas-orchestrator.service` - Systemd service definition
