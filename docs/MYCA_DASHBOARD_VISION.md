# MYCA Dashboard Vision & Requirements
**Priority**: #1 (Core Functionality - Must Work ASAP)  
**URL**: `localhost:3100`  
**Date**: January 15, 2026

---

## 🎯 Executive Summary

MYCA Dashboard is the **ONLY** interface for MAS operations. It should be the single source of truth for staff, administrators, and operators to monitor and control the Multi-Agent System.

**Key Principle**: 
> "If you need to know something about MAS, MYCA Dashboard should tell you. If you need to do something with MAS, MYCA Dashboard should do it."

---

## 🏗️ Architecture Role

```
┌─────────────────────────────────────────────────────────────────┐
│                        MYCOSOFT ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   CUSTOMERS                           STAFF/OPERATORS           │
│       │                                      │                   │
│       ▼                                      ▼                   │
│  ┌─────────────┐                    ┌─────────────────┐         │
│  │   WEBSITE   │                    │ MYCA DASHBOARD  │ ◄── YOU │
│  │   (3000)    │                    │     (3100)      │   ARE   │
│  │             │                    │                 │   HERE  │
│  │ - NatureOS  │                    │ - Agent Control │         │
│  │ - Devices   │                    │ - System Health │         │
│  │ - Public    │                    │ - Workflows     │         │
│  └─────────────┘                    │ - Integrations  │         │
│                                     │ - Monitoring    │         │
│                                     └────────┬────────┘         │
│                                              │                   │
│                                              ▼                   │
│                                    ┌─────────────────┐          │
│                                    │  BACKEND APIS   │          │
│                                    │ 8000/8001/8003  │          │
│                                    └─────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Core Requirements

### 1. Service Health Monitoring

**Every service must be visible in MYCA Dashboard with:**
- Real-time status (online/offline/degraded)
- Latency metrics
- Last check timestamp
- Quick action buttons (restart, configure)

```
┌─────────────────────────────────────────────────────────────────┐
│ 🏥 SERVICE HEALTH PANEL                              [Refresh]  │
├──────────────┬──────┬────────┬─────────┬───────────────────────┤
│ Service      │ Port │ Status │ Latency │ Details              │
├──────────────┼──────┼────────┼─────────┼───────────────────────┤
│ MINDEX API   │ 8000 │ 🟢 UP  │ 12ms    │ v1.2.0, 150 records  │
│ MAS Orchestr │ 8001 │ 🟢 UP  │ 8ms     │ 15 agents active     │
│ MycoBrain    │ 8003 │ 🟢 UP  │ 15ms    │ 3 devices connected  │
│ N8n Workflows│ 5678 │ 🟢 UP  │ 45ms    │ 5/12 workflows active│
│ Qdrant       │ 6345 │ 🟢 UP  │ 5ms     │ 2.1M vectors stored  │
│ Redis        │ 6379 │ 🟢 UP  │ 1ms     │ 1.2GB / 4GB used     │
│ PostgreSQL   │ 5432 │ 🟢 UP  │ 3ms     │ 15 active connections│
│ Grafana      │ 3002 │ 🟢 UP  │ 120ms   │ 0 dashboards         │
│ Prometheus   │ 9090 │ 🟢 UP  │ 8ms     │ 50 scrape targets    │
│ Website      │ 3000 │ 🟢 UP  │ 25ms    │ Next.js running      │
└──────────────┴──────┴────────┴─────────┴───────────────────────┘
```

### 2. Agent Management

**Full visibility and control of all 40+ agents:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AGENT REGISTRY                                    [+ New]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ [Search agents...]                   [Category ▼] [Status ▼]   │
│                                                                  │
│ CORE AGENTS ─────────────────────────────────────────           │
│ ┌───────────────────┐ ┌───────────────────┐ ┌─────────────────┐│
│ │ 🟢 Project Manager│ │ 🟢 Dashboard Agent│ │ 🟢 Secretary    ││
│ │ 15 tasks running  │ │ Idle              │ │ 3 reminders     ││
│ └───────────────────┘ └───────────────────┘ └─────────────────┘│
│                                                                  │
│ FINANCIAL AGENTS ────────────────────────────────────           │
│ ┌───────────────────┐ ┌───────────────────┐ ┌─────────────────┐│
│ │ 🟢 Finance Agent  │ │ 🟡 Token Economics│ │ 🟢 Admin Finance││
│ │ Budget tracking   │ │ API rate limited  │ │ Approvals ready ││
│ └───────────────────┘ └───────────────────┘ └─────────────────┘│
│                                                                  │
│ MYCOLOGY AGENTS ─────────────────────────────────────           │
│ ┌───────────────────┐ ┌───────────────────┐ ┌─────────────────┐│
│ │ 🟢 Mycology Bio   │ │ 🟢 Species DB     │ │ 🟢 Knowledge    ││
│ │ 2 analyses active │ │ 12,450 species    │ │ Ready           ││
│ └───────────────────┘ └───────────────────┘ └─────────────────┘│
│                                                                  │
│ [Show 35 more agents...]                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3. MycoBrain Device Monitoring

**Real-time ESP32 device status:**

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ MYCOBRAIN DEVICE NETWORK                         [+ Register]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  DEVICE NETWORK MAP                         ││
│  │                                                             ││
│  │      [MCB-001]────────[MCB-002]                            ││
│  │         │                 │                                 ││
│  │         └────[MCB-003]────┘                                ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ MCB-001     │ │ MCB-002     │ │ MCB-003     │               │
│  │ 🟢 Online   │ │ 🟢 Online   │ │ 🟡 Warning  │               │
│  │ Temp: 23°C  │ │ Temp: 24°C  │ │ Temp: 31°C  │ ◄ High temp  │
│  │ Hum: 67%    │ │ Hum: 65%    │ │ Hum: 45%    │               │
│  │ Up: 14d 3h  │ │ Up: 7d 12h  │ │ Up: 2h 30m  │               │
│  │ [Configure] │ │ [Configure] │ │ [Configure] │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. N8n Workflow Status

**Quick view of automation status:**

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ N8N WORKFLOWS                           [Open N8n Console →] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ACTIVE WORKFLOWS (5)                                            │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ Daily Backup           Running    Last: 2 min ago       │ │
│ │ ✅ System Health Check    Running    Last: 30 sec ago      │ │
│ │ ✅ Alert Notification     Running    Last: 5 min ago       │ │
│ │ ✅ Data Sync              Running    Last: 1 min ago       │ │
│ │ ✅ Report Generation      Running    Last: 1 hour ago      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ INACTIVE WORKFLOWS (7)                                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ⏸️ Quarterly Report       Paused     [Activate]            │ │
│ │ ⏸️ User Onboarding        Paused     [Activate]            │ │
│ │ ...                                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5. System Topology (Already Exists - Enhance)

Current topology view is good, enhance with:
- Real-time connection health
- Data flow visualization
- Click-through to entity details
- Filter by entity type

### 6. Quick Actions Panel

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ QUICK ACTIONS                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ [🔄 Restart All Agents]  [📊 Generate Report]  [🔍 Run Scan]   │
│                                                                  │
│ [📦 Backup Database]     [🔧 Clear Cache]      [📝 View Logs]  │
│                                                                  │
│ [⚙️ System Settings]     [👥 User Management]  [🔑 API Keys]   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 API Integration Requirements

MYCA Dashboard must call these endpoints:

### Health Checks (Every 10 seconds):
```typescript
const healthEndpoints = [
  { service: 'MINDEX', url: 'http://localhost:8000/health' },
  { service: 'MAS Orchestrator', url: 'http://localhost:8001/health' },
  { service: 'MycoBrain', url: 'http://localhost:8003/health' },
  { service: 'Website', url: 'http://localhost:3000/api/health' },
];
```

### N8n Integration:
```typescript
// Get workflow status
GET http://localhost:5678/api/v1/workflows
Authorization: Bearer ${N8N_API_KEY}

// Get execution history
GET http://localhost:5678/api/v1/executions
```

### MycoBrain Devices:
```typescript
// Get all devices
GET http://localhost:8003/devices

// Get device telemetry
GET http://localhost:8003/devices/{device_id}/telemetry
```

### Database Stats:
```typescript
// Qdrant collections
GET http://localhost:6345/collections

// Redis info (via API wrapper)
GET http://localhost:3000/api/redis/info

// PostgreSQL connections
GET http://localhost:3000/api/postgres/stats
```

---

## 📊 Dashboard Layout

### Main Views:

1. **Overview** (Default)
   - System health summary
   - Active agents count
   - Recent activity feed
   - Quick stats

2. **Topology**
   - Network visualization
   - Entity connections
   - Real-time updates

3. **Agents**
   - Full agent list
   - Status and controls
   - Task management

4. **Devices**
   - MycoBrain devices
   - Sensor data
   - Configuration

5. **Workflows**
   - N8n status
   - Execution history
   - Quick controls

6. **Integrations**
   - External services
   - API connections
   - Webhooks

7. **Settings**
   - System configuration
   - User management
   - API keys

---

## 🎨 Visual Requirements

### Design System:
- Follow UniFi-style dark theme
- Background: `#0F172A` (dark blue-gray)
- Cards: `#1E293B` (lighter blue-gray)
- Accent: `#3B82F6` (blue) for primary actions
- Success: `#22C55E` (green)
- Warning: `#F59E0B` (amber)
- Error: `#EF4444` (red)

### Typography:
- Use Inter for UI text
- Use monospace for data/IDs
- Clear hierarchy with sizes

### Animations:
- Subtle transitions (200ms)
- Pulse for live indicators
- Smooth data updates

---

## 📋 Implementation Checklist

### High Priority (ASAP):
- [ ] Add Service Health Panel with all endpoints
- [ ] Connect to MycoBrain API for device status
- [ ] Connect to N8n API for workflow status
- [ ] Add database stats (Qdrant, Redis, Postgres)
- [ ] Add Quick Actions panel

### Medium Priority:
- [ ] Enhance topology with real-time data flow
- [ ] Add execution history from N8n
- [ ] Add log viewer for all services
- [ ] Add alert/notification system

### Lower Priority:
- [ ] Add user management
- [ ] Add API key management
- [ ] Add backup controls
- [ ] Add advanced settings

---

## 🔗 Links to Other Interfaces

MYCA Dashboard should have quick links to:

| Interface | URL | Purpose |
|-----------|-----|---------|
| Website | localhost:3000 | Public site |
| N8n Console | localhost:5678 | Workflow editor |
| Grafana | localhost:3002 | Detailed metrics |
| Prometheus | localhost:9090 | Raw metrics |
| API Docs | localhost:8000/docs | MINDEX API |
| API Docs | localhost:8001/docs | MAS Orchestrator |
| API Docs | localhost:8003/docs | MycoBrain |

---

## 📝 Notes

1. **MYCA is for STAFF ONLY** - not customers
2. **Everything in one place** - no switching between tools
3. **Real-time updates** - no manual refresh needed
4. **Quick actions** - common tasks one click away
5. **Mobile responsive** - accessible from any device

---

*Document created: January 15, 2026*
*Priority: Must be functional ASAP*
