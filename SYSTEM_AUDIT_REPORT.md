# System Audit Report - January 6, 2025

## Executive Summary

**Overall Status**: ⚠️ **OPERATIONAL WITH ISSUES**

Most core services are running, but several issues require attention:
- 2 containers not running (MycoBrain, n8n-importer)
- 2 containers unhealthy (Website, Ollama)
- 1 port configuration issue (MYCA app)
- 1 service running outside Docker (MycoBrain on port 8003)

---

## ✅ Services Running Correctly

### Core Services
- ✅ **Website** (Port 3000) - Running, accessible (health check cosmetic issue)
- ✅ **MAS Orchestrator** (Port 8001) - Healthy, responding
- ✅ **MINDEX** (Port 8000) - Healthy, responding
- ✅ **PostgreSQL** (Port 5433) - Healthy
- ✅ **Redis** (Port 6390) - Healthy
- ✅ **Qdrant** (Port 6345) - Healthy
- ✅ **Unifi Dashboard** (Port 3100) - Healthy
- ✅ **n8n** (Port 5678) - Running
- ✅ **Whisper** (Port 8765) - Healthy
- ✅ **Voice UI** (Port 8090) - Running
- ✅ **TTS** (Port 10200) - Running
- ✅ **OpenEDAI Speech** (Port 5500) - Running

---

## ⚠️ Issues Found

### 1. **CRITICAL: MycoBrain Container Not Running**
- **Container**: `mycosoft-always-on-mycobrain-1`
- **Status**: Created (not started)
- **Impact**: Device management API unavailable in Docker
- **Workaround**: MycoBrain service running directly on host (PID 89080, Port 8003)
- **Action Required**: Start container or verify host service is sufficient

```powershell
# To start the container:
docker-compose -f docker-compose.always-on.yml up -d mycobrain

# Or verify host service:
Get-Process -Id 89080
```

### 2. **MYCA App Port Configuration Issue**
- **Container**: `mycosoft-mas-myca-app-1`
- **Issue**: Shows `3000/tcp` but should be mapped to `3001:3000`
- **Expected**: External port 3001, internal port 3000
- **Current**: No external port mapping shown
- **Impact**: MYCA dashboard may not be accessible on expected port
- **Action Required**: Verify docker-compose.yml port mapping

### 3. **Website Health Check Failing (Non-Critical)**
- **Container**: `mycosoft-always-on-mycosoft-website-1`
- **Status**: Unhealthy (but website is working)
- **Issue**: Health check endpoint `/api/health` returns HTTP 207
- **Impact**: Cosmetic only - website is fully functional
- **Action Required**: Fix health check endpoint or adjust health check command

### 4. **Ollama Container Unhealthy**
- **Container**: `mycosoft-mas-ollama-1`
- **Status**: Unhealthy (but service appears to be running)
- **Port**: 11434 (accessible)
- **Issue**: Health check failing, but logs show service is listening
- **Impact**: Local LLM functionality may work despite health check failure
- **Action Required**: Review health check configuration or ignore if service works

### 5. **n8n Importer Exited**
- **Container**: `mycosoft-mas-n8n-importer-1`
- **Status**: Exited (0) 6 days ago
- **Impact**: Workflow imports may not have run
- **Action Required**: Verify workflows are imported, restart if needed

### 6. **Grafana Not Running**
- **Expected Port**: 3002
- **Status**: Not found in running containers
- **Impact**: Monitoring dashboards unavailable
- **Action Required**: Start Grafana service if monitoring is needed
- **Note**: May be intentionally stopped if not using monitoring

### 7. **Prometheus Not Running**
- **Expected Port**: 9090
- **Status**: Not found in running containers
- **Impact**: Metrics collection unavailable
- **Action Required**: Start Prometheus service if metrics are needed
- **Note**: May be intentionally stopped if not using metrics

---

## 📊 Port Status Summary

| Port | Service | Status | Notes |
|------|---------|--------|-------|
| 3000 | Website | ✅ Listening | Working correctly |
| 3001 | MYCA App | ✅ Listening | Port mapping issue |
| 3002 | Grafana | ❌ Not Running | Service not started |
| 8000 | MINDEX | ✅ Listening | Healthy |
| 8001 | MAS API | ✅ Listening | Healthy |
| 8003 | MycoBrain | ⚠️ Listening | Running on host, not Docker |
| 3100 | Unifi Dashboard | ✅ Listening | Healthy |
| 5678 | n8n | ✅ Listening | Running |
| 9090 | Prometheus | ❌ Not Running | Service not started |
| 11434 | Ollama | ⚠️ Listening | Unhealthy |

---

## 🔍 Resource Usage

### High CPU Usage
- **Node Process (PID 59080)**: 8370 CPU units, 2710 MB memory
  - Likely the MYCA app or website
  - May need optimization if performance issues occur

### Docker Processes
- Multiple Docker processes running normally
- Total Docker memory usage: ~600 MB

---

## 🛠️ Recommended Actions

### Immediate (High Priority)
1. **Start MycoBrain Container**:
   ```powershell
   docker-compose -f docker-compose.always-on.yml up -d mycobrain
   ```

2. **Fix MYCA App Port Mapping**:
   - Check `docker-compose.yml` for `myca-app` service
   - Ensure ports are `"3001:3000"`

3. **Start Monitoring Services**:
   ```powershell
   docker-compose up -d grafana prometheus
   ```

### Medium Priority
4. **Fix Ollama Health Check**:
   ```powershell
   docker logs mycosoft-mas-ollama-1 --tail 50
   # Investigate health check failures
   ```

5. **Restart n8n Importer** (if workflows need importing):
   ```powershell
   docker-compose restart n8n-importer
   ```

### Low Priority (Non-Critical)
6. **Fix Website Health Check**:
   - Update health check to use root path `/` instead of `/api/health`
   - Or fix `/api/health` endpoint to return proper status code

---

## ✅ Verification Checklist

- [x] Website accessible on port 3000
- [x] MAS API responding on port 8001
- [x] MINDEX responding on port 8000
- [x] Database services healthy
- [x] Core infrastructure running
- [ ] MycoBrain container running
- [ ] MYCA app accessible on port 3001
- [ ] Grafana accessible on port 3002
- [ ] Prometheus accessible on port 9090
- [ ] Ollama healthy
- [ ] All health checks passing

---

## 📝 Notes

1. **MycoBrain Service**: Currently running as a host process (PID 89080) on port 8003. This works but should ideally run in Docker for consistency.

2. **Website Health Check**: The "unhealthy" status is cosmetic - the website is fully functional. The health check endpoint returns HTTP 207 which wget treats as an error.

3. **Port Conflicts**: No active port conflicts detected. All services are on their assigned ports.

4. **System Stability**: Core services have been running for 2+ hours without issues, indicating good stability.

---

## Next Steps

1. Address the 3 critical issues (MycoBrain container, MYCA port, monitoring services)
2. Monitor system for 24 hours after fixes
3. Verify all health checks pass
4. Document any additional issues found
