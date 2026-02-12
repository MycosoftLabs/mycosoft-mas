# Mycosoft System Status - Current
**Date**: February 12, 2026  
**Status**: ✅ OPERATIONAL  

## Primary URLs

| Service | URL | Status | Notes |
|---------|-----|--------|-------|
| **Website Dev** | http://localhost:3010 | ✅ Active | Dev server - ONLY port for dev |
| **Website Prod** | http://sandbox.mycosoft.com | ✅ Active | VM 187, port 3000 |
| **CREP Dashboard** | http://localhost:3010/dashboard/crep | ✅ Active | Part of website |
| **NatureOS** | http://localhost:3010/natureos | ✅ Active | Part of website |
| **AI Studio** | http://localhost:3010/natureos/ai-studio | ✅ Active | MYCA interface |
| **Test Voice** | http://localhost:3010/test-voice | ✅ Active | Voice testing |
| **MAS Orchestrator** | http://192.168.0.188:8001 | ✅ Running | VM 188 |
| **MINDEX API** | http://192.168.0.189:8000 | ✅ Running | VM 189 |
| **MycoBrain Service** | http://localhost:8003 | ✅ Running | Local service |
| **n8n Workflows** | http://192.168.0.188:5678 | ✅ Running | VM 188 |

## DEPRECATED - DO NOT USE

| Service | URL | Status |
|---------|-----|--------|
| ~~MAS Dashboard~~ | ~~http://localhost:3001~~ | ❌ DEPRECATED |
| ~~MYCA UniFi Dashboard~~ | ~~http://localhost:3100~~ | ❌ DEPRECATED |
| ~~unifi-dashboard/~~ | ~~MAS/mycosoft-mas/unifi-dashboard/~~ | ❌ DEPRECATED |

**WARNING**: The `unifi-dashboard` directory in MAS repo is deprecated. All website work must be done in `WEBSITE/website/` repo only.

## CREP Dashboard Features

The CREP (Common Relevant Environmental Picture) dashboard at `/dashboard/crep` provides:

### Live Statistics (As of Last Check)
- **73 Active Events** - Real-time global event monitoring
- **1 Device** - Connected MycoBrain devices
- **0 Critical** - No critical alerts

### Data Feeds
- **Earthquakes** - USGS real-time feed
- **Volcanoes** - Global volcanic activity monitoring
- **Wildfires** - NIFC/IRWIN fire data
- **Storms** - Tropical cyclone tracking
- **Fungal Events** - MINDEX observations integration

### Dashboard Tabs
- **MSSN** - Active mission status (Global Fungal Network Monitoring @ 67%)
- **DATA** - Data sources and feeds
- **INTEL** - Intelligence feed
- **LYRS** - Map layers control
- **SVCS** - Connected services
- **MYCA** - MYCA agent integration

### MINDEX Kingdoms (Species Database)
- **Fungi**: 1,247,000 entries
- **Plants**: 380,000 entries
- **Birds**: 10,000 entries
- **Insects**: 950,000 entries
- **Animals**: 68,000 entries
- **Marine**: 245,000 entries

## Hardware Status

### MycoBrain Device (COM5)
```
Device ID: mycobrain-COM5
Port: COM5
Status: Connected
Firmware: 3.3.5
Board: ESP32-S3
CPU: 240 MHz
PSRAM: OPI PSRAM
Flash: 16 MB

Sensors:
- AMB (0x77): T=23.58°C, RH=32.14%, P=709.24hPa
- ENV (0x76): T=23.75°C, RH=28.65%, P=645.65hPa

Controls:
- LED: RGB NeoPixel (SK6805)
- Buzzer: GPIO16
- MOSFETs: GPIO12, GPIO13, GPIO14
- I2C: SDA=5, SCL=4 @ 100kHz
```

## Port Assignments

### Core Services
| Port | Service | Description | Location |
|------|---------|-------------|----------|
| **3010** | **Website Dev** | Next.js dev server (LOCAL ONLY) | Local PC |
| **3000** | **Website Prod** | Next.js production container | VM 187 |
| **8000** | **MINDEX API** | Fungal database API | VM 189 |
| **8001** | **MAS Orchestrator** | FastAPI orchestrator | VM 188 |
| **8003** | **MycoBrain** | Device management API | Local |
| **3002** | **Grafana** | Monitoring dashboards | Local/VM |

### DEPRECATED Ports (DO NOT USE)
| Port | Service | Status |
|------|---------|--------|
| ~~3001~~ | ~~MAS Dashboard~~ | ❌ DEPRECATED |
| ~~3100~~ | ~~MYCA UniFi~~ | ❌ DEPRECATED |

### Infrastructure
| Port | Service |
|------|---------|
| 5432/5433 | PostgreSQL |
| 6379 | Redis |
| 6333 | Qdrant |
| 9090 | Prometheus |
| 5678 | n8n Workflows |

## Integration Flow

```
CREP Dashboard (localhost:3000/dashboard/crep)
  ├── MINDEX (localhost:8000) → Fungal observations
  ├── MycoBrain Service (localhost:8003) → IoT devices
  ├── MAS Orchestrator (localhost:8001) → 42+ agents
  └── External APIs
      ├── USGS Earthquake Feed
      ├── NIFC Wildfire Data
      ├── NOAA Weather/Space Weather
      └── FlightRadar24/AIS Maritime
```

## Quick Start Commands

### Start Website Dev Server (CORRECT WAY)
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev:next-only
# URL: http://localhost:3010
```

**WARNING**: NEVER run `npm run dev` from the MAS repo. The `unifi-dashboard/` is DEPRECATED.

### Start MycoBrain Service
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\mycobrain
python mycobrain_service_standalone.py
# Or use: .\scripts\mycobrain-service.ps1 start
```

### Access Main Pages (Dev)
```
Website Home:      http://localhost:3010
CREP Dashboard:    http://localhost:3010/dashboard/crep
Device Manager:    http://localhost:3010/natureos/devices
NatureOS:          http://localhost:3010/natureos
AI Studio:         http://localhost:3010/natureos/ai-studio
Test Voice:        http://localhost:3010/test-voice
```

### VM Services (Production)
```
Website (Sandbox): http://sandbox.mycosoft.com (VM 187:3000)
MAS API:           http://192.168.0.188:8001
MINDEX API:        http://192.168.0.189:8000
```

## System Health Indicators

- **● SYSTEM OPERATIONAL** - All core services running
- **UPTIME: 99.9%** - High availability maintained
- **MYCOBRAIN: CONNECTED** - Hardware devices online
- **MINDEX: SYNCED** - Database synchronized
- **MYCA: ACTIVE** - AI agents operational

---

## IMPORTANT: Website Development

**The website is in a SEPARATE repo from MAS:**

| Purpose | Repo Path |
|---------|-----------|
| **Website (Next.js)** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\` |
| **MAS (Python Backend)** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\` |

- All UI pages, components, and frontend work must be done in the **WEBSITE repo**
- The `unifi-dashboard/` directory in MAS repo is **DEPRECATED** and must never be used
- Dev server always runs on port **3010** from the website repo

---

**Last Updated**: February 12, 2026
