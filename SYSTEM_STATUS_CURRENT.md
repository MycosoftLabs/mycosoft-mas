# Mycosoft System Status - Current
**Date**: January 16, 2026, 5:22 PM PST  
**Status**: ✅ OPERATIONAL  

## Primary URLs

| Service | URL | Status |
|---------|-----|--------|
| **Mycosoft Website** | http://localhost:3000 | ✅ Running |
| **CREP Dashboard** | http://localhost:3000/dashboard/crep | ✅ Active |
| **NatureOS** | http://localhost:3000/natureos | ✅ Active |
| **Device Manager** | http://localhost:3000/natureos/devices | ✅ Active |
| **MAS Orchestrator** | http://localhost:8001 | ✅ Running |
| **MINDEX** | http://localhost:8000 | ✅ Healthy |
| **MycoBrain Service** | http://localhost:8003 | ✅ Running |
| **MYCA UniFi Dashboard** | http://localhost:3100 | ✅ Running |
| **Grafana** | http://localhost:3002 | ✅ Running |
| **n8n Workflows** | http://localhost:5678 | ✅ Running |

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
| Port | Service | Description |
|------|---------|-------------|
| **3000** | **Website** | Mycosoft Next.js website (RESERVED) |
| **3001** | **MYCA App** | MAS Dashboard (DEPRECATED) |
| **3002** | **Grafana** | Monitoring dashboards |
| **3100** | **MYCA UniFi** | Voice integration dashboard |
| **8000** | **MINDEX** | Fungal database API |
| **8001** | **MAS Orchestrator** | FastAPI orchestrator |
| **8003** | **MycoBrain** | Device management API |

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

### Start Website (if not running)
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
npm run dev
```

### Start MycoBrain Service
```powershell
cd services\mycobrain
python mycobrain_service_standalone.py
```

### Start Docker Services
```powershell
docker-compose -f docker-compose.always-on.yml up -d
```

### Access Main Dashboards
```
CREP Dashboard:    http://localhost:3000/dashboard/crep
Device Manager:    http://localhost:3000/natureos/devices
NatureOS:          http://localhost:3000/natureos
```

## System Health Indicators

- **● SYSTEM OPERATIONAL** - All core services running
- **UPTIME: 99.9%** - High availability maintained
- **MYCOBRAIN: CONNECTED** - Hardware devices online
- **MINDEX: SYNCED** - Database synchronized
- **MYCA: ACTIVE** - AI agents operational

---

**Last Updated**: January 16, 2026 @ 5:22 PM PST
