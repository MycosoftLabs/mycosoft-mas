# Port & Service Requirements Document
**Version**: 1.0  
**Date**: January 15, 2026  
**Status**: Planning & Documentation Phase

---

## 📋 Executive Summary

This document defines all ports, services, and their integration requirements for the Mycosoft MAS ecosystem. Each service is categorized by its role and documented with specific requirements for UI integration, health monitoring, and user accessibility.

---

## 🎯 Priority Hierarchy

| Priority | Interface | URL | Purpose |
|----------|-----------|-----|---------|
| **#1** | MYCA Dashboard | `localhost:3100` | THE central MAS orchestrator UI |
| **#2** | NatureOS | `localhost:3000/natureos` | Customer demo & business showcase |
| **#3** | Devices Page | `localhost:3000/devices` | Visual device management (needs styling) |
| **#4** | Website | `localhost:3000` | Public-facing website |

---

## 🌐 Complete Port Reference

### 🟢 USER-FACING INTERFACES (Priority Focus)

| Port | Service | Has UI? | Integrated to MYCA? | Integrated to Website? | Requirements |
|------|---------|---------|---------------------|------------------------|--------------|
| **3000** | Website (Next.js) | ✅ Yes | N/A | Self | Main public interface |
| **3100** | MYCA Dashboard | ✅ Yes | Self | ⚠️ Needs link | THE central orchestrator |
| **3002** | Grafana | ✅ Yes | ❌ No | ❌ No | Metrics dashboards needed |

### 🟡 BACKEND APIs (Need Health Integration)

| Port | Service | Has UI? | Integrated to MYCA? | Integrated to Website? | Requirements |
|------|---------|---------|---------------------|------------------------|--------------|
| **8000** | MINDEX API | Swagger only | ⚠️ Partial | ❌ No | Health status in MYCA |
| **8001** | MAS Orchestrator | Swagger only | ⚠️ Partial | ❌ No | Core backend - needs monitoring |
| **8003** | MycoBrain API | Swagger only | ⚠️ Partial | ⚠️ Partial | Device health in MYCA |
| **5678** | N8n Workflows | ✅ Full UI | ⚠️ Partial | ❌ No | Workflow status integration |
| **9090** | Prometheus | ✅ Full UI | ❌ No | ❌ No | Metrics source for Grafana |

### 🔵 DATABASE/INFRASTRUCTURE (No UI Needed - CLI/API Only)

| Port | Service | Has UI? | Integrated to MYCA? | Integrated to Website? | Requirements |
|------|---------|---------|---------------------|------------------------|--------------|
| **5432/5433** | PostgreSQL | ❌ CLI only | ❌ No | ❌ No | Health check only |
| **6379** | Redis | ❌ CLI only | ❌ No | ❌ No | Health/stats in MYCA |
| **6333/6345** | Qdrant | REST API only | ❌ No | ❌ No | Vector DB stats in MYCA |
| **3101** | Loki | ❌ Internal | ❌ No | ❌ No | Log aggregation |

### ❌ NOT RUNNING / DEPRECATED

| Port | Service | Status | Action Needed |
|------|---------|--------|---------------|
| **6390** | Redis Insight | Not running | Optional - can use CLI |

---

## 📊 Detailed Service Requirements

### 1. MYCA Dashboard (Port 3100) - THE Priority

**Current State**: Functional but needs full integration
**Target State**: Single source of truth for all MAS operations

#### Required Features:
```
┌─────────────────────────────────────────────────────────────┐
│ MYCA DASHBOARD - Required Integrations                      │
├─────────────────────────────────────────────────────────────┤
│ ✅ Agent Management      │ View/control all 40+ agents      │
│ ✅ System Topology       │ Network visualization            │
│ ⚠️ Health Monitoring     │ All service health endpoints     │
│ ⚠️ Device Status         │ MycoBrain ESP32 devices          │
│ ⚠️ Workflow Status       │ N8n active workflows             │
│ ❌ Database Stats        │ Qdrant, PostgreSQL, Redis        │
│ ❌ Real-time Metrics     │ CPU, Memory, Docker containers   │
│ ❌ Service Health Panel  │ All ports in one view            │
└─────────────────────────────────────────────────────────────┘
```

#### Health Endpoints to Integrate:
| Service | Health Endpoint | What to Display |
|---------|-----------------|-----------------|
| MINDEX | `GET /health` | Status, version |
| MAS Orchestrator | `GET /health` | Status, uptime |
| MycoBrain | `GET /health` | Status, device count |
| N8n | `GET /api/v1/workflows` | Active workflow count |
| Qdrant | `GET /collections` | Collection count, vectors |
| Redis | `redis-cli PING` | Connectivity |
| PostgreSQL | `pg_isready` | Database status |

---

### 2. NatureOS (Port 3000/natureos) - Demo Priority

**Current State**: Functional with basic styling
**Target State**: Premium demo experience for customers

#### Required Features:
- ✅ System monitoring dashboard
- ✅ Earth Simulator integration
- ✅ Live data feeds
- ⚠️ MYCA chat interface (needs enhancement)
- ⚠️ MycoBrain device widget (needs real data)
- ❌ Parallax effects and premium animations
- ❌ Custom typography and branding
- ❌ Touch/mobile optimizations

---

### 3. Devices Page (Port 3000/devices) - Visual Priority

**Current State**: Functional but plain
**Target State**: Visually stunning device management

#### Visual Requirements:
- ❌ Parallax video backgrounds in hero area
- ❌ Custom fonts (non-standard)
- ❌ Animated transitions
- ❌ Scroll-triggered effects
- ❌ Touch/swipe interactions
- ❌ 3D device visualizations
- ❌ Premium color scheme

---

### 4. Service Health Status Requirements

Each backend service needs a health widget in MYCA:

```typescript
interface ServiceHealth {
  service: string;
  port: number;
  status: 'online' | 'offline' | 'degraded';
  latency: number;
  lastCheck: Date;
  version?: string;
  details?: Record<string, unknown>;
}
```

#### Health Panel Layout:
```
┌────────────────────────────────────────────────────────┐
│ SERVICE HEALTH PANEL                          [Refresh]│
├───────────┬───────┬────────┬─────────┬────────────────┤
│ Service   │ Port  │ Status │ Latency │ Details        │
├───────────┼───────┼────────┼─────────┼────────────────┤
│ MINDEX    │ 8000  │ 🟢     │ 12ms    │ v1.2.0         │
│ MAS API   │ 8001  │ 🟢     │ 8ms     │ 15 agents      │
│ MycoBrain │ 8003  │ 🟢     │ 15ms    │ 3 devices      │
│ N8n       │ 5678  │ 🟢     │ 45ms    │ 5 workflows    │
│ Qdrant    │ 6345  │ 🟢     │ 5ms     │ 2M vectors     │
│ Redis     │ 6379  │ 🟢     │ 1ms     │ 1.2GB used     │
│ Postgres  │ 5432  │ 🟢     │ 3ms     │ 15 connections │
│ Grafana   │ 3002  │ 🟢     │ 120ms   │ 3 dashboards   │
│ Prometheus│ 9090  │ 🟢     │ 8ms     │ 50 targets     │
└───────────┴───────┴────────┴─────────┴────────────────┘
```

---

## 🔧 API Endpoints Summary

### Website API Routes (`localhost:3000/api/...`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/system` | GET | System stats (CPU, RAM, Docker) | ✅ Working |
| `/api/health` | GET | Website health | ✅ Working |
| `/api/metrics` | GET | System metrics | ✅ Working |
| `/api/network` | GET | Network devices | ✅ Working |
| `/api/mycobrain/devices` | GET | ESP32 devices | ✅ Working |
| `/api/mycobrain/health` | GET | MycoBrain health | ⚠️ Needs work |
| `/api/n8n` | GET | N8n status | ✅ Working |
| `/api/mas/topology` | GET | MAS topology | ✅ Working |
| `/api/agents/registry` | GET | Agent list | ✅ Working |

### External Service APIs

| Service | Base URL | Key Endpoints |
|---------|----------|---------------|
| MINDEX | `localhost:8000` | `/health`, `/docs`, `/api/v1/...` |
| MAS Orchestrator | `localhost:8001` | `/health`, `/docs`, `/agents/...` |
| MycoBrain | `localhost:8003` | `/health`, `/docs`, `/devices/...` |
| N8n | `localhost:5678` | `/api/v1/workflows` |
| Qdrant | `localhost:6345` | `/collections`, `/points/...` |

---

## 📝 Integration Checklist

### For MYCA Dashboard (3100):
- [ ] Add service health panel with all endpoints
- [ ] Add device status from MycoBrain (8003)
- [ ] Add workflow count from N8n (5678)
- [ ] Add database stats (Qdrant, Redis, Postgres)
- [ ] Add real-time system metrics
- [ ] Connect to all agent endpoints

### For Website (3000):
- [ ] Add link to MYCA Dashboard in navigation
- [ ] Add service health indicator in footer/header
- [ ] Add NatureOS showcase improvements
- [ ] Add Devices page visual enhancements

### For Grafana (3002):
- [ ] Create MAS Agents dashboard
- [ ] Create System Health dashboard
- [ ] Create MycoBrain Devices dashboard
- [ ] Configure Prometheus data source

---

## 🎨 Visual Integration Standards

All integrations should follow:
- **Dark theme**: `#0F172A` (background), `#1E293B` (cards)
- **Accent colors**: Green (#22C55E), Blue (#3B82F6), Purple (#8B5CF6)
- **Status indicators**: Green (online), Yellow (degraded), Red (offline)
- **Typography**: Inter for UI, Space Grotesk for headers (website)
- **Animations**: Subtle, 200-300ms transitions

---

## 📌 Notes

1. **Port 6390 (Redis Insight)**: Not critical - Redis works via CLI
2. **Port 3002 (Grafana)**: Empty because no dashboards provisioned yet
3. **Qdrant (6345)**: REST API only, no web UI - this is by design
4. **MYCA (3100) is the ONLY dashboard** staff should use for MAS operations
5. **Website (3000)** is for customers and public access

---

*Document created: January 15, 2026*
*Next review: After implementation*
