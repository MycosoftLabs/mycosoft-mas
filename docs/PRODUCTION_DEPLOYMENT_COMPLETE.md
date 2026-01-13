# MYCA Production Deployment - Complete Guide

## Overview

This document summarizes the complete production deployment for MYCA (Mycosoft Autonomous Cognitive Agent) system, covering all infrastructure, services, and operational procedures.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                     mycosoft.com (Cloudflare)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Website VM (192.168.20.11)     API VM (192.168.20.10)              │
│  ┌─────────────────────┐        ┌─────────────────────────┐         │
│  │ nginx (:80)         │        │ MAS API (:8001)         │         │
│  │ Next.js (:3000)     │◄──────►│ MINDEX (:8000)          │         │
│  │ PM2 Cluster         │        │ NatureOS (:8002)        │         │
│  └─────────────────────┘        │ n8n (:5678)             │         │
│                                 │ Dashboard (:3100)       │         │
│                                 │ 42+ Background Agents   │         │
│                                 └───────────┬─────────────┘         │
│                                             │                        │
│                                             ▼                        │
│                         Database VM (192.168.20.12)                 │
│                         ┌─────────────────────────┐                 │
│                         │ PostgreSQL 16 (:5432)   │                 │
│                         │ Redis 7 (:6379)         │                 │
│                         │ Qdrant (:6333)          │                 │
│                         └───────────┬─────────────┘                 │
│                                     │                                │
│                                     ▼                                │
│                         NAS (192.168.0.1:/mycosoft)                 │
│                         26TB Storage                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Infrastructure Components

### 1. Virtual Machines (Proxmox)

| VM | IP | Node | Resources | Services |
|----|-----|------|-----------|----------|
| myca-website | 192.168.20.11 | DC1 | 4 CPU, 8GB RAM, 50GB | nginx, Next.js, PM2 |
| myca-api | 192.168.20.10 | Build | 8 CPU, 32GB RAM, 100GB | MAS API, MINDEX, n8n, Dashboard, Agents |
| myca-database | 192.168.20.12 | DC2 | 4 CPU, 16GB RAM, 200GB | PostgreSQL, Redis, Qdrant |

### 2. NAS Storage Structure

```
/mnt/mycosoft/
├── databases/       # DB persistence (secured)
├── knowledge/       # MINDEX, encyclopedia (public read)
├── agents/          # Agent workloads
├── website/         # Static assets, uploads
├── backups/         # Automated backups (root only)
├── secure/          # Staff SSH only
└── monitoring/      # Prometheus/Grafana data
```

### 3. Cloudflare Configuration

**DNS Records (via Tunnel):**
- `mycosoft.com` → Website VM
- `www.mycosoft.com` → Website VM
- `api.mycosoft.com` → API VM
- `dashboard.mycosoft.com` → Dashboard (Staff Only)
- `webhooks.mycosoft.com` → n8n Webhooks

**Access Policies:**
- Public: mycosoft.com, www.mycosoft.com
- Staff Only: dashboard.mycosoft.com, /admin/*
- Super Admin: /debug/*

## Deployment Scripts

All deployment scripts are located in `scripts/production/`:

| Script | Purpose |
|--------|---------|
| `create_all_vms.py` | Create VMs on Proxmox |
| `vm_setup_common.sh` | Common VM setup (Docker, NFS, etc) |
| `setup_database_vm.sh` | Database services setup |
| `setup_api_vm.sh` | API services setup |
| `setup_website_vm.sh` | Website setup |
| `setup_cloudflare_tunnel.sh` | Cloudflare tunnel configuration |
| `setup_monitoring.sh` | Prometheus/Grafana stack |
| `migrate_databases.sh` | Data migration |
| `nas_security.sh` | NAS access controls |
| `create_staff_accounts.ts` | Staff user creation |
| `go_live_checklist.sh` | Pre-launch verification |

## Staff Accounts

| Name | Email | Role | Access |
|------|-------|------|--------|
| Morgan | morgan@mycosoft.com | super_admin | Full system access |
| Alberto | alberto@mycosoft.com | admin | Backend, admin panel |
| Garrett | garrett@mycosoft.com | admin | Security focus |
| Abelardo | abelardo@mycosoft.com | developer | Code, debugging |
| RJ | rj@mycosoft.com | developer | Code, debugging |
| Chris | chris@mycosoft.com | developer | Code, debugging |

**Authentication:**
- Primary: Google OAuth
- Backup: Email/Password

## Services

### MAS API (Port 8001)
- Agent orchestration
- Task management
- Voice processing
- WebSocket connections

### MINDEX (Port 8000)
- Species database
- Encyclopedia search
- Vector embeddings
- Taxonomy browser

### NatureOS (Port 8002)
- Earth simulator API
- Weather data
- Geological events
- Biological tracking

### n8n (Port 5678)
- Workflow automation
- MycoBrain integration
- Notification system
- Data pipelines

### Dashboard (Port 3100)
- Real-time monitoring
- Agent status
- System metrics
- Voice interface

## Website Features

### Implemented
- Home page
- Search (MINDEX integration)
- Encyclopedia browser
- Earth Simulator
- Device management
- User authentication

### Staff-Only
- Admin panel
- Debug endpoints
- System dashboard
- Agent management

## MycoBrain Integration

### API Endpoints
- `POST /api/devices/register` - Device registration
- `POST /api/devices/telemetry` - Data ingestion
- `GET /api/devices` - List devices

### Data Flow
```
MycoBrain Device
      │
      ▼ HTTP/MQTT
  myca-api:8001
      │
      ├──► PostgreSQL (time-series)
      ├──► n8n (alerts/workflows)
      └──► Dashboard (real-time)
```

## Monitoring

### Stack
- **Prometheus** (9090) - Metrics collection
- **Grafana** (3002) - Dashboards
- **Loki** (3100) - Log aggregation
- **Promtail** - Log shipping

### Alerts
- Service health
- Resource usage
- Error rates
- Response times

## Backup Strategy

### Daily (2 AM)
- PostgreSQL full dump
- Redis RDB snapshot
- Qdrant collection snapshots

### Weekly (Sunday 3 AM)
- Full NAS backup
- Configuration backup
- Docker image backup

### Disaster Recovery
- Off-site replication (planned)
- Azure failover (prepared)

## Security Measures

### Network
- VLAN segmentation (Mgmt, Prod, Agents, IoT)
- Firewall rules per VM
- Internal service mesh

### Application
- JWT authentication
- Role-based access control
- Rate limiting (100 req/min API)
- Input validation

### Infrastructure
- SSH key authentication only
- No root password login
- Automatic security updates
- Audit logging

## Go-Live Checklist

Run `scripts/production/go_live_checklist.sh` to verify:

- [ ] All VMs reachable
- [ ] Database services healthy
- [ ] API endpoints responding
- [ ] Website accessible
- [ ] SSL certificates valid
- [ ] Security headers present
- [ ] Monitoring active
- [ ] Backups verified

## Operational Commands

### Check Service Status
```bash
# On any VM
systemctl status myca-*

# Docker services
docker compose ps
```

### View Logs
```bash
# Website
pm2 logs myca-website

# API services
docker compose logs -f myca-api
```

### Restart Services
```bash
# Website
pm2 restart all

# API
systemctl restart myca-api

# Database
systemctl restart myca-database
```

### Database Access
```bash
# PostgreSQL
docker exec -it myca-postgres psql -U mas

# Redis
docker exec -it myca-redis redis-cli
```

## Troubleshooting

### Website Not Loading
1. Check nginx: `systemctl status nginx`
2. Check PM2: `pm2 status`
3. Check tunnel: `systemctl status cloudflared`

### API Errors
1. Check containers: `docker compose ps`
2. View logs: `docker compose logs myca-api`
3. Check DB connectivity

### Database Issues
1. Check PostgreSQL: `docker exec myca-postgres pg_isready`
2. Check Redis: `docker exec myca-redis redis-cli ping`
3. Check NAS mount: `df -h /mnt/mycosoft`

## Contact

- **Super Admin**: Morgan (morgan@mycosoft.com)
- **Engineering Lead**: Alberto (alberto@mycosoft.com)
- **Security**: Garrett (garrett@mycosoft.com)

---

*Last Updated: January 10, 2026*
*Version: 1.0.0*
