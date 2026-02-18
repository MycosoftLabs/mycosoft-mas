# MAS VM Issues and Fixes - February 12, 2026

## Current Status (After Fixes Applied)

| Component | Status | Notes |
|-----------|--------|-------|
| mas-orchestrator | ✅ Running | systemd service on port 8001 |
| PostgreSQL | ✅ Healthy | Connected to MINDEX VM (189:5432) - **FIXED** |
| Redis | ✅ Healthy | Running on localhost:6379 |
| Collectors | ⚠️ Degraded | Optional - external data collectors not running |
| Agent Containers | ⚠️ Stopped | 17 legacy containers stopped 9 days ago |
| N8N | ✅ Running | But missing `myca/voice` webhook |
| Disk | ⚠️ 85% full | 15G free of 98G |

---

## Fixes Applied (Feb 12, 2026)

### Fix 1: Database Connection - RESOLVED ✅

**Problem:** The MAS `.env` file was missing `DATABASE_URL` and the systemd service wasn't loading env files.

**Solution Applied:**
1. Added database configuration to `/home/mycosoft/mycosoft/mas/.env`:
   ```
   DATABASE_URL=postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex
   MINDEX_DATABASE_URL=postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex
   POSTGRES_HOST=192.168.0.189
   POSTGRES_PORT=5432
   POSTGRES_USER=mycosoft
   POSTGRES_PASSWORD=REDACTED_DB_PASSWORD
   POSTGRES_DB=mindex
   REDIS_HOST=localhost
   REDIS_PORT=6379
   MINDEX_API_URL=http://192.168.0.189:8000
   QDRANT_HOST=192.168.0.189
   QDRANT_PORT=6333
   ```

2. Updated systemd service (`/etc/systemd/system/mas-orchestrator.service`) to load .env file:
   ```ini
   [Service]
   ...
   EnvironmentFile=/home/mycosoft/mycosoft/mas/.env
   ...
   ```

3. Reloaded systemd and restarted service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart mas-orchestrator
   ```

**Result:** PostgreSQL health check now shows "healthy" with ~78ms latency.

---

## Remaining Issues

### Issue 1: Collectors Not Running (Optional)

**Status:** ⚠️ Degraded (not critical)

**What are collectors?** External data collectors for CREP system:
- OpenSkyCollector (aviation)
- USGSCollector (earthquakes)
- NORADCollector (satellites)
- AISCollector (maritime)
- NOAACollector (weather)

**Why not running?** Collectors are not started automatically on MAS startup. They need to be explicitly started.

**To start collectors:**
```python
from mycosoft_mas.collectors import start_default_collectors
await start_default_collectors()
```

Or via API:
```bash
curl -X POST http://192.168.0.188:8001/api/crep/collectors/start
```

**Recommendation:** Leave as-is unless CREP data collection is needed. The "degraded" status doesn't affect core MAS functionality.

---

### Issue 2: Agent Runner Failures

**Status:** ⚠️ Warning - agent cycles failing silently

**Error log:**
```
ERROR:mycosoft_mas.core.agent_runner:Cycle LoadedRunnerAgent_20260212_... failed:
WARNING:agent.research:Unknown task type: continuous_cycle
```

**Root Cause:** Agents are receiving tasks with type `continuous_cycle` which they don't handle.

**Impact:** Background agent cycles may not be executing properly.

**Fix:** Investigate `mycosoft_mas/core/agent_runner.py` and add handler for `continuous_cycle` task type.

---

### Issue 3: Legacy Docker Containers Stopped

**Status:** ⚠️ 17 containers stopped for 9 days

**Stopped containers (from old Docker deployment approach):**
- myca-metabase, myca-metabase-db
- mas-agent-openai-connector, mas-agent-n8n-integration
- mas-agent-etl-processor, mas-agent-mindex-agent
- mas-agent-network-monitor, mas-agent-docker-manager
- mas-agent-proxmox-monitor, mas-agent-hr-manager
- mas-agent-legal, mas-agent-financial
- mas-agent-message-broker, mas-agent-health-monitor
- mas-agent-task-router, mas-agent-memory-manager
- mas-agent-myca-orchestrator, mas-agent-test-agent-1

**Recommendation:** These appear to be from an old Docker-based deployment that was replaced by the systemd service. Remove them to free disk space:

```bash
# Remove stopped containers
docker rm myca-metabase myca-metabase-db mas-agent-openai-connector \
  mas-agent-n8n-integration mas-agent-etl-processor mas-agent-mindex-agent \
  mas-agent-network-monitor mas-agent-docker-manager mas-agent-proxmox-monitor \
  mas-agent-hr-manager mas-agent-legal mas-agent-financial mas-agent-message-broker \
  mas-agent-health-monitor mas-agent-task-router mas-agent-memory-manager \
  mas-agent-myca-orchestrator mas-agent-test-agent-1

# Remove unused images
docker image prune -a -f
```

---

### Issue 4: N8N Webhook Missing

**Status:** ⚠️ Voice workflow not configured

**Error:** `Error triggering workflow myca/voice: 404 Not Found`

**Impact:** Voice system can't trigger N8N workflows for processing.

**Fix Options:**
1. Create the `myca/voice` webhook in N8N (http://192.168.0.188:5678)
2. Or update MAS code to not require this webhook

---

### Issue 5: Disk Usage at 85%

**Current:** 79G used of 98G (15G free)

**Fix:** Clean up Docker resources:
```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Check large directories
du -sh /home/mycosoft/* | sort -h
du -sh /var/lib/docker/* | sort -h
```

---

## Running Services (Healthy)

| Service | Port | Type |
|---------|------|------|
| mas-orchestrator | 8001 | systemd service |
| mycorrhizae-api | 8002 | Docker container |
| myca-n8n | 5678 | Docker container |
| mas-redis | 6379 | Docker container |

---

## Verification Commands

```bash
# Check MAS health
curl -s http://192.168.0.188:8001/health | python3 -m json.tool

# Check service status
sudo systemctl status mas-orchestrator

# Check recent logs
journalctl -u mas-orchestrator --no-pager | tail -50

# Check .env is loaded
cat /proc/$(pgrep -f "uvicorn mycosoft_mas")/environ | tr '\0' '\n' | grep DATABASE
```
