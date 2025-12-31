# Docker Integration Plan - Mycosoft System
**Date**: December 30, 2025  
**Status**: Active Deployment  

## System Architecture

### Core Services (Always-On)
```
Port 3000: Mycosoft Website (Docker)
Port 8000: MINDEX Data Index (Docker)
Port 8001: MAS Orchestrator (Docker)
Port 8003: MycoBrain Service (Local Python - needs COM port access)
Port 5678: n8n Workflow Automation (Docker)
Port 3100: MYCA UniFi Dashboard (Docker)
```

### Service Dependencies
```mermaid
Website (3000)
  ├─> MINDEX (8000) - Species/device data
  ├─> MycoBrain (8003) - Device telemetry
  ├─> MAS (8001) - Agent orchestration
  └─> n8n (5678) - Workflow triggers

MycoBrain (8003)
  ├─> COM5 Serial Port (ESP32-S3)
  └─> PostgreSQL (MAS database)

MINDEX (8000)
  ├─> PostgreSQL (MAS database)
  ├─> GBIF API (external)
  ├─> Index Fungorum (external)
  └─> iNaturalist API (external)

MAS (8001)
  ├─> n8n (5678)
  ├─> Qdrant (6345)
  ├─> Redis (6390)
  └─> PostgreSQL (5433)
```

## Docker Compose Structure

### Production (docker-compose.always-on.yml)
- **Website**: Next.js 15 with React 18
- **MINDEX**: FastAPI with taxonomic reconciliation
- **MAS Components**: Orchestrator, agents, databases
- **n8n**: Workflow automation
- **MYCA Dashboard**: UniFi-style interface

### Key Environment Variables
```bash
# Website
MYCOBRAIN_SERVICE_URL=http://host.docker.internal:8003
NEXT_PUBLIC_API_URL=http://localhost:3000
NODE_ENV=production

# MINDEX
DATABASE_URL=postgresql://postgres:postgres@mas-postgres:5432/mas_db
GBIF_API_URL=https://api.gbif.org/v1
INDEX_FUNGORUM_URL=https://www.indexfungorum.org

# MAS
MAS_DATABASE_URL=postgresql://postgres:postgres@mas-postgres:5432/mas_db
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379
```

## Integration Points

### 1. Website → MycoBrain
**Endpoint**: `/api/mycobrain/*`
**Purpose**: Device management, telemetry, control
**Status**: ✓ Working
**Routes**:
- `GET /api/mycobrain/devices` - List devices
- `POST /api/mycobrain/devices` - Connect/disconnect
- `GET /api/mycobrain/ports` - Scan serial ports
- `GET /api/mycobrain/[port]/sensors` - Get sensor data
- `POST /api/mycobrain/[port]/control` - Send commands

### 2. Website → MINDEX
**Endpoint**: `/api/mindex/*`
**Purpose**: Species data, taxonomy, search
**Status**: ✓ Working
**Routes**:
- `GET /api/mindex/health` - Health check
- `GET /api/mindex/stats` - Statistics
- `POST /api/mindex/species/match` - GBIF matching
- `GET /api/mindex/devices` - Device list

### 3. MycoBrain → Hardware
**Protocol**: Serial (115200 baud)
**Port**: COM5
**Device**: ESP32-S3 (MycoBrain v1)
**Firmware**: 3.3.5
**Status**: ✓ Connected
**Features**:
- BME688 sensors (AMB + ENV)
- NeoPixel RGB LED
- Buzzer/coin sounds
- 4x MOSFET outputs
- I2C bus scanning

### 4. MINDEX → External APIs
**GBIF**: Species backbone matching
**Index Fungorum**: Fungal nomenclature
**iNaturalist**: Observation data
**Status**: ✓ Working

## Known Issues & Solutions

### Issue 1: `initialTimeout is not defined`
**Root Cause**: Old cached build in Docker image  
**Solution**: Complete rebuild with cache clearing (IN PROGRESS)
**Steps**:
1. Stop all containers
2. Remove old images
3. Clear .next and node build caches
4. Clear Docker build cache
5. Rebuild with `--no-cache`

### Issue 2: MycoBrain Cannot Run in Docker
**Root Cause**: Serial port access requires host privileges  
**Solution**: Run MycoBrain service on host, not in Docker
**Status**: ✓ Implemented
**Details**: Website uses `host.docker.internal:8003` to reach local service

### Issue 3: Port Conflicts
**Root Cause**: Multiple processes trying to bind same port  
**Solution**: Systematic port management script
**Status**: ✓ Implemented in rebuild script

## Deployment Strategy

### Local Development (Docker Desktop)
- Use `docker-compose.always-on.yml`
- MycoBrain runs on host for COM port access
- All other services in Docker
- Resource limits: 4GB RAM, 2 CPUs per container

### Production (Docker Cloud - Future)
- Same architecture, but MycoBrain via USB/IP forwarding
- Or: Separate hardware node with MycoBrain service
- Full telemetry streaming to cloud database

## Testing Checklist

### Basic Connectivity
- [ ] Website loads on port 3000
- [ ] Device Manager page loads without errors
- [ ] MINDEX health check returns 200
- [ ] MycoBrain health check returns 200
- [ ] MAS orchestrator health check returns 200

### MycoBrain Integration
- [ ] COM5 device appears in port scan
- [ ] Device connects successfully
- [ ] Sensor data displays in UI
- [ ] LED controls work (Red, Green, Blue)
- [ ] Buzzer/sound controls work
- [ ] MOSFET controls work
- [ ] I2C scan detects BME688 sensors

### MINDEX Integration
- [ ] Species search returns results
- [ ] GBIF matching works
- [ ] Index Fungorum data loads
- [ ] Taxonomic reconciliation functions

### End-to-End Workflows
- [ ] Device telemetry → PostgreSQL → Website display
- [ ] User control command → MycoBrain → Device response
- [ ] Species search → MINDEX → GBIF → Results
- [ ] n8n workflow → Device automation

## Cost Optimization

### Local (Docker Desktop)
- **Cost**: $0/month
- **Limitations**: Single machine, no redundancy
- **Best for**: Development, testing, small deployments

### Cloud (Future)
- **Consider**: Docker Cloud, AWS ECS, Azure Container Instances
- **Estimated**: $50-100/month for full stack
- **Benefits**: Scalability, redundancy, remote access

## Maintenance

### Daily
- Monitor Docker container health
- Check MycoBrain connection status
- Review n8n workflow execution logs

### Weekly
- Update Docker images (security patches)
- Backup PostgreSQL database
- Review MINDEX data quality

### Monthly
- Update firmware on MycoBrain devices
- Review and optimize Docker resource usage
- Test disaster recovery procedures

## Next Steps (Post-Fix)

1. **Add Monitoring**: Prometheus + Grafana
2. **Add Logging**: ELK stack or Loki
3. **Add Backups**: Automated PostgreSQL backups
4. **Add CI/CD**: GitHub Actions for automated builds
5. **Add Documentation**: API docs with Swagger/OpenAPI
6. **Add Tests**: Integration tests for all services

## Emergency Contacts

**System Admin**: User (you)
**MycoBrain Hardware**: COM5 on local machine
**Database**: PostgreSQL on mas-postgres container
**Logs**: `docker logs <container-name>`

---
**Last Updated**: Rebuild in progress...

