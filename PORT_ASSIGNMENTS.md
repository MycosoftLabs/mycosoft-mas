# Port Assignments - Mycosoft MAS

## Standard Port Configuration

**CRITICAL: Port 3000 is RESERVED for the Website ONLY**

### Core Services

| Port | Service | Description | Access |
|------|---------|-------------|--------|
| **3000** | **Website** | Next.js website (mycosoft.com) | http://localhost:3000 |
| **3001** | **MYCA App** | MAS Dashboard (Next.js) | http://localhost:3001 |
| **3002** | **Grafana** | Monitoring dashboards | http://localhost:3002 |
| **8000** | **MINDEX** | Always-on service | http://localhost:8000 |
| **8001** | **MAS Orchestrator** | FastAPI orchestrator | http://localhost:8001 |
| **8003** | **MycoBrain Service** | Device management API | http://localhost:8003 |
| **3100** | **MICA Unifi Dashboard** | Voice integration dashboard | http://localhost:3100 |
| **5500** | **Open EDAI Speech** | Speech service | http://localhost:5500 |
| **8765** | **Whisper** | STT service | http://localhost:8765 |

### Infrastructure Services

| Port | Service | Description |
|------|---------|-------------|
| **5432** | **PostgreSQL** | Database (internal) |
| **5433** | **PostgreSQL** | Database (external mapping) |
| **6379** | **Redis** | Cache and message broker |
| **6333** | **Qdrant** | Vector database |
| **9090** | **Prometheus** | Metrics collector |
| **5678** | **n8n** | Workflow automation |

## Port Conflicts Resolution

### Issue
- Grafana was configured to use port 3000
- This conflicted with the website
- Port assignments were inconsistent across documentation

### Solution
- **Port 3000**: Reserved exclusively for the website
- **Port 3002**: Grafana moved to this port
- **Port 3001**: MYCA app (MAS dashboard) uses this port

## Configuration Files Updated

1. `config/config.yaml` - Grafana port changed from 3000 to 3002
2. All docker-compose files should map Grafana to port 3002
3. Documentation updated to reflect correct port assignments

## Verification

To verify port assignments:

```powershell
# Check what's running on each port
netstat -ano | findstr ":3000 :3001 :3002"

# Test website (should be on 3000)
curl http://localhost:3000

# Test MYCA app (should be on 3001)
curl http://localhost:3001

# Test Grafana (should be on 3002)
curl http://localhost:3002
```

## Important Notes

- **NEVER** configure Grafana to use port 3000
- **NEVER** configure MYCA app to use port 3000
- Port 3000 is **ONLY** for the website
- If you see port 3000 being used by anything other than the website, it's a configuration error
