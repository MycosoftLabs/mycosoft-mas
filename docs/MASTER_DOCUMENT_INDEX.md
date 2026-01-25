# MYCOSOFT MASTER DOCUMENT INDEX

**Version**: 1.4.0  
**Date**: 2026-01-17  
**Last Updated**: 2026-01-24 23:00 UTC  
**Total Documents**: 200+ (January 15-24, 2026)

---

## 📑 TABLE OF CONTENTS

1. [System Overview Documents](#system-overview-documents)
2. [Deployment Guides](#deployment-guides)
3. [MycoBrain Documentation](#mycobrain-documentation)
4. [Security & Compliance](#security--compliance)
5. [API & Integration Guides](#api--integration-guides)
6. [Infrastructure & DevOps](#infrastructure--devops)
7. [Feature Documentation](#feature-documentation)
8. [Troubleshooting & Fixes](#troubleshooting--fixes)
9. [Planning & Roadmaps](#planning--roadmaps)
10. [Codebase Structure](#codebase-structure)

---

## 📋 SYSTEM OVERVIEW DOCUMENTS

### Primary Briefing Documents

| Document | Path | Purpose |
|----------|------|---------|
| **[V1 Deployment Complete](./MYCOSOFT_V1_DEPLOYMENT_COMPLETE.md)** | docs/ | **START HERE** - Full system overview |
| [90-Day Scaling Plan](./SCALING_PLAN_90_DAYS.md) | docs/ | Infrastructure roadmap |
| [Security Audit](./SECURITY_AUDIT_JAN17_2026.md) | docs/ | Security overview |
| [Port Assignments](../PORT_ASSIGNMENTS.md) | root | All service ports |
| [README](../README.md) | root | Quick start guide |

### Master Status Documents

| Document | Date | Content |
|----------|------|---------|
| **[MASTER_STATUS_JAN24_2026.md](./MASTER_STATUS_JAN24_2026.md)** | **Jan 24** | **Complete system integration status, MYCA VM preparation** |

### Session Summaries

| Document | Date | Content |
|----------|------|---------|
| **SESSION_SUMMARY_JAN23_2026.md** | Jan 23 | Network/security audit, topology scanning |
| **SESSION_SUMMARY_JAN22_2026.md** | Jan 22 | MINDEX page, MycoNode/SporeBase updates |
| **SESSION_SUMMARY_JAN20_2026_EVENING.md** | Jan 20 | MycoBrain fix, deployment |
| **SESSION_SUMMARY_JAN20_2026.md** | Jan 20 | Device lookup fix |
| **STAFF_BRIEFING_JAN20_2026.md** | Jan 20 | Staff-friendly summary |
| DEPLOYMENT_SESSION_JAN19_2026_TODAY.md | Jan 19 | Mushroom1 media deployment |
| SESSION_SUMMARY_JAN16_2026_FINAL.md | Jan 16 | Complete day summary |
| DOCUMENTATION_SUMMARY_JAN17_2026.md | Jan 16 | Doc organization |
| COMPREHENSIVE_BROWSER_TESTING_REPORT.md | Jan 15 | Browser test results |

### System Architecture

| Document | Purpose |
|----------|---------|
| **SYSTEM_ARCHITECTURE_OVERVIEW_JAN2026.md** | Complete system topology |
| MASTER_ARCHITECTURE.md | Detailed component design |
| PORT_SERVICE_REQUIREMENTS.md | Port assignments |

### Chemistry Integration (Jan 24)

| Document | Purpose |
|----------|---------|
| **CHEMSPIDER_INTEGRATION.md** | ChemSpider API integration guide |
| AGENT_REGISTRY.md (v2.1) | Updated with 8 chemistry agents |

### MAS v2 Architecture (NEW - Jan 24)

| Document | Purpose |
|----------|---------|
| **[MAS_V2_COMPLETE_DOCUMENTATION.md](./MAS_V2_COMPLETE_DOCUMENTATION.md)** | **Complete MAS v2 implementation documentation** |
| [MAS_V2_IMPLEMENTATION_SUMMARY.md](./MAS_V2_IMPLEMENTATION_SUMMARY.md) | Implementation summary and metrics |
| [MAS_VM_PROVISIONING_GUIDE.md](./MAS_VM_PROVISIONING_GUIDE.md) | VM provisioning guide (16 cores, 64GB) |
| [DASHBOARD_COMPONENTS.md](./DASHBOARD_COMPONENTS.md) | Dashboard component specifications |
| **[MYCA_VM_DEPLOYMENT_PREPARATION.md](./MYCA_VM_DEPLOYMENT_PREPARATION.md)** | **Step-by-step MYCA orchestrator VM deployment** |

#### MAS v2 Key Implementation Files

| Path | Description |
|------|-------------|
| `mycosoft_mas/runtime/` | Agent runtime engine (9 files) |
| `mycosoft_mas/agents/v2/` | 40 agent classes (6 files) |
| `mycosoft_mas/core/orchestrator_service.py` | MYCA orchestrator upgrade |
| `mycosoft_mas/core/dashboard_api.py` | Real-time dashboard API |
| `docker/Dockerfile.agent` | Agent container image |
| `docker/docker-compose.agents.yml` | Agent deployment stack |
| `migrations/003_agent_logging.sql` | Database schema additions |

---

## 🚀 DEPLOYMENT GUIDES

### VM & Server Setup

| Document | Purpose |
|----------|---------|
| COMPLETE_VM_DEPLOYMENT_GUIDE.md | Full VM setup instructions |
| PROXMOX_VM_SPECIFICATIONS.md | Proxmox configuration |
| VM103_DEPLOYMENT_COMPLETE.md | Sandbox VM status |
| VM_POST_INSTALLATION_GUIDE.md | Post-install steps |
| VM_MAINTENANCE_BACKUP_GUIDE.md | Backup procedures |
| VM_QUICK_REFERENCE.md | Quick access commands |

### Docker & Containers

| Document | Purpose |
|----------|---------|
| DOCKER_STATUS.md | Container status |
| DOCKER_INTEGRATION_PLAN.md | Integration guide |
| MYCOSOFT_STACK_DEPLOYMENT.md | Stack deployment |

### Network & Cloudflare

| Document | Purpose |
|----------|---------|
| CLOUDFLARE_TUNNEL_SETUP.md | Tunnel configuration |
| SERVER_MIGRATION_MASTER_GUIDE.md | Migration procedures |
| MIGRATION_CHECKLIST.md | Migration checklist |
| **NETWORK_INFRASTRUCTURE_JAN21_2026.md** | Complete network topology after Jan 21 recabling |

### Network & Security Tools

| Script | Purpose |
|--------|---------|
| `scripts/network_topology_scanner.py` | Scan network, identify bottlenecks, generate audit reports |
| `scripts/security_audit_scanner.py` | API auth testing, secrets detection, infrastructure scan |

### Configuration Guides

| Document | Purpose |
|----------|---------|
| **API_TOKEN_REGENERATION_GUIDE.md** | Step-by-step guide for Proxmox & UniFi API token setup |
| PROXMOX_UNIFI_API_REFERENCE.md | API endpoints and current token reference |

### Security Audit Reports

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_SUMMARY_JAN23_2026.md** | Commit hash, tested routes, issues found |
| **SANITY_CHECK_REPORT_JAN23_2026.md** | Website sanity check - no loops/runaway requests |
| **SNAPSHOT_ROLLBACK_POINT_JAN23_2026.md** | VM snapshot & rollback instructions |
| **ROUTE_VERIFICATION_REPORT_JAN23_2026.md** | NatureOS/MYCA route verification |
| **AUTH_VERIFICATION_REPORT_JAN23_2026.md** | Authentication flow verification |
| SECURITY_AUDIT_*.md | Generated security audit reports |
| security_audit_*.json | Machine-readable security data |
| AUTH_TEST_REPORT_*.md | Authentication test results |

### Authentication Tools

| Script | Purpose |
|--------|---------|
| `scripts/auth_flow_tester.py` | Comprehensive auth flow testing |

### Media Assets & NAS

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_INSTRUCTIONS_MASTER.md** | Complete deployment reference |
| **NAS_MEDIA_INTEGRATION.md** | NAS mount setup |
| **RUNBOOK_NAS_MEDIA_WEBSITE_ASSETS.md** | Media deployment runbook |
| **AGENT_HANDOFF_NAS_MEDIA_INTEGRATION.md** | Agent handoff notes |
| MEDIA_ASSETS_PIPELINE.md | Media sync pipeline |

---

## 🧠 MYCOBRAIN DOCUMENTATION

### Hardware & Firmware

| Document | Purpose |
|----------|---------|
| MYCOBRAIN_SYSTEM_ARCHITECTURE.md | Complete architecture |
| MYCOBRAIN_README.md | Getting started |
| MYCOBRAIN_COMMAND_REFERENCE.md | CLI commands |
| MYCOBRAIN_QUICKSTART.md | Quick start guide |
| FIRMWARE_UPGRADE_READY.md | Firmware status |

### Setup & Configuration

| Document | Purpose |
|----------|---------|
| MYCOBRAIN_SETUP_COMPLETE.md | Setup status |
| MYCOBRAIN_SETUP_INSTRUCTIONS.md | Setup steps |
| MYCOBRAIN_SETUP_FINAL_STATUS.md | Final status |
| setup_mycobrain_bridge.md | Bridge configuration |
| **MYCOBRAIN_TROUBLESHOOTING_GUIDE.md** | Troubleshooting reference |
| **MYCOBRAIN_FIX_JAN20_2026.md** | Device lookup fix |

### Testing & Status

| Document | Purpose |
|----------|---------|
| MYCOBRAIN_SYSTEM_TEST_REPORT.md | Test results |
| MYCOBRAIN_COMPLETE_STATUS_REPORT.md | Full status |
| MYCOBRAIN_CURRENT_STATUS_JAN_16_2026.md | Jan 16 status |
| MYCOBRAIN_STATUS_UPDATE_JAN_16_2026.md | Status update |
| **MYCOBRAIN_CONNECTION_REPORT_JAN23_2026.md** | Jan 23 - COM7 connected via VM bridge |

### Device Manager

| Document | Purpose |
|----------|---------|
| MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_EXPLANATION.md | Machine mode |
| MYCOBRAIN_DEVICE_MANAGER_MACHINE_MODE_INTEGRATION.md | Integration |
| MYCOBRAIN_WEBSITE_INTEGRATION.md | Website integration |

---

## 🔐 SECURITY & COMPLIANCE

| Document | Purpose | Priority |
|----------|---------|----------|
| **SECURITY_AUDIT_JAN17_2026.md** | Full security audit | 🔴 Critical |
| ENV_TEMPLATE.md | Environment template | Medium |
| env.example | Example config | Medium |

---

## 🔌 API & INTEGRATION GUIDES

### API Documentation

| Document | Purpose |
|----------|---------|
| CREP_DATA_SOURCE_APIS.md | CREP API sources |
| PROXMOX_UNIFI_API_REFERENCE.md | Infrastructure APIs |
| INTEGRATION_SETUP_GUIDE.md | Integration guide |
| INTEGRATION_SUMMARY.md | Integration overview |

### MINDEX

| Document | Purpose |
|----------|---------|
| MINDEX_FILE_FIX.md | File fixes |
| MINDEX_ETL_SCHEDULER_FIX.md | ETL scheduler |

### NatureOS

| Document | Purpose |
|----------|---------|
| NATUREOS_INTEGRATION_ANALYSIS.md | Integration analysis |
| NATUREOS_INTEGRATION_COMPLETE.md | Integration complete |
| NATUREOS_OEI_INTEGRATION_PLAN.md | OEI integration |
| NATUREOS_OEI_AUDIT_UPDATE.md | OEI audit |
| NATUREOS_VISION.md | Product vision |

---

## 🏗️ INFRASTRUCTURE & DEVOPS

### Production & Deployment

| Document | Purpose |
|----------|---------|
| PRODUCTION_DEPLOYMENT_CHECKLIST.md | Deploy checklist |
| PRODUCTION_READINESS_REPORT.md | Readiness status |
| PRODUCTION_RUNBOOK.md | Operations guide |
| QUICK_START.md | Quick start |

### Monitoring

| Document | Purpose |
|----------|---------|
| prometheus.yml | Metrics config |
| alertmanager.yml | Alert routing |
| grafana/ | Dashboard configs |

---

## 🎨 FEATURE DOCUMENTATION

### CREP Dashboard

| Document | Purpose |
|----------|---------|
| CREP_USER_PERSONA_TESTS.md | User testing |
| CREP_AIRCRAFT_VESSEL_CRASH_FIX.md | Bug fixes |
| CREP_WEBSITE_DEPLOYMENT_REFERENCE.md | Deployment ref |

### Devices & Hardware

| Document | Purpose |
|----------|---------|
| DEVICES_PAGE_VISION.md | Devices page design |
| DEVICE_RECOVERY_STATUS.md | Recovery procedures |
| DEVICE_STATUS_SUMMARY.md | Device status |

### MYCA AI

| Document | Purpose |
|----------|---------|
| MYCA_DASHBOARD_VISION.md | Dashboard vision |
| MYCA_BOOTSTRAP_READY.md | Bootstrap status |
| MYCA_IMPROVEMENTS_SUMMARY.md | Improvements |

---

## 🔧 TROUBLESHOOTING & FIXES

### Bug Fixes

| Document | Issue Fixed |
|----------|-------------|
| BUG_FIX_FINAL_SOLUTION.md | Various fixes |
| CRITICAL_ISSUE_RESOLUTION.md | Critical issues |
| CREP_AIRCRAFT_VESSEL_CRASH_FIX.md | Marker crashes |
| CURSOR_CRASH_FIX_COMPLETE.md | IDE issues |
| PORT_CONFLICT_RESOLUTION.md | Port conflicts |

### Service Fixes

| Document | Issue Fixed |
|----------|-------------|
| SERVICES_FIXED_REPORT.md | Service issues |
| WEBSITE_PORT_3000_PERMANENT_FIX.md | Port 3000 |
| WEBSITE_PORT_FIX.md | Port fix |
| WEBSITE_RUNNING_CONFIRMED.md | Confirmation |

### System Fixes

| Document | Issue Fixed |
|----------|-------------|
| SYSTEM_AUDIT_AND_FIXES.md | Audit fixes |
| SYSTEM_FIXES_APPLIED.md | Applied fixes |
| SYSTEM_ISSUES_REPORT.md | Issue report |
| MAS_CORRUPTION_FIX.md | MAS fix |

---

## 📅 PLANNING & ROADMAPS

| Document | Purpose |
|----------|---------|
| SCALING_PLAN_90_DAYS.md | 90-day scale plan |
| IMPLEMENTATION_ROADMAP.md | Implementation plan |
| UPGRADE_PLAN.md | Upgrade planning |
| SCIENCECOMMS_FIRMWARE_UPGRADE_PLAN.md | Firmware upgrade |
| SIDE_A_SIDE_B_FIRMWARE_PLAN.md | A/B firmware |

---

## 📁 CODEBASE STRUCTURE

### Website (C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\)

```
website/
├── app/                          # Next.js 15 App Router
│   ├── api/                      # 131 API routes
│   │   ├── ai/                   # AI endpoints
│   │   ├── ancestry/             # Ancestry API
│   │   ├── compounds/            # Compound analysis
│   │   ├── crep/                 # CREP dashboard
│   │   ├── devices/              # Device management
│   │   ├── earth-simulator/      # Earth sim
│   │   ├── mindex/               # MINDEX API
│   │   ├── myca/                 # MYCA AI
│   │   ├── mycobrain/            # MycoBrain API
│   │   ├── natureos/             # NatureOS
│   │   ├── oei/                  # Earth Intelligence
│   │   ├── search/               # Search API
│   │   └── species/              # Species API
│   ├── (pages)/                  # Page routes
│   │   ├── about/
│   │   ├── ancestry/
│   │   ├── apps/
│   │   ├── dashboard/crep/       # CREP Dashboard
│   │   ├── devices/
│   │   ├── mindex/
│   │   ├── myca-ai/
│   │   └── natureos/             # NatureOS pages
│   └── components/               # React components
│       ├── crep/                 # CREP components
│       ├── earth-simulator/      # Simulator components
│       ├── mindex/               # MINDEX components
│       └── ui/                   # shadcn/ui components
├── lib/                          # Utility libraries
├── services/                     # Backend services
│   └── mycobrain/                # MycoBrain Python service
├── public/                       # Static assets
└── docker-compose*.yml           # Docker configs
```

### MAS (C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\)

```
mycosoft-mas/
├── agents/                       # AI agent definitions
├── docs/                         # 155+ documentation files
├── firmware/                     # ESP32 MycoBrain firmware
│   ├── mycobrain/               # Main firmware
│   ├── sciencecomms/            # Science mode
│   └── test/                    # Test firmware
├── n8n/                         # Workflow automation
│   ├── workflows/               # Workflow definitions
│   └── credentials/             # API credentials
├── orchestrator-myca/           # MYCA orchestration
├── services/                    # Backend services
│   ├── mindex/                  # MINDEX service
│   └── mycobrain/              # MycoBrain service
├── speech/                      # Voice UI
│   ├── ui/                      # Voice interface
│   └── tts/                     # Text-to-speech
├── unifi-dashboard/             # UniFi-style dashboard
├── grafana/                     # Grafana dashboards
├── prometheus/                  # Prometheus config
├── config/                      # Configuration files
│   ├── development.env
│   ├── production.env
│   └── config.yaml
└── docker-compose*.yml          # Docker configs
```

### MINDEX (C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\)

```
mindex/
├── api/                         # FastAPI backend
├── etl/                         # Data pipelines
├── schemas/                     # Database schemas
└── docker-compose.yml           # Container config
```

### Firmware (firmware/)

```
firmware/
├── mycobrain/                   # Production firmware
│   ├── src/                     # Source code
│   ├── lib/                     # Libraries
│   └── platformio.ini          # Build config
├── sciencecomms/               # Science communication mode
└── test/                       # Test firmware
```

---

## 🔗 QUICK LINKS

### Primary Endpoints

| Endpoint | URL |
|----------|-----|
| Website (Local) | http://localhost:3000 |
| Website (Sandbox) | https://sandbox.mycosoft.com |
| MINDEX API | http://localhost:8000 |
| MycoBrain Service | http://localhost:8003 |
| n8n Workflows | http://localhost:5678 |
| Grafana | http://localhost:3002 |

### SSH Access

```bash
ssh mycosoft@192.168.0.187
```

### Docker Commands

```bash
# View all containers
docker ps

# View logs
docker logs mycosoft-website

# Restart website
docker restart mycosoft-website
```

---

## 📝 DOCUMENT MAINTENANCE

### How to Update This Index

1. Add new documents to appropriate section
2. Update last modified date
3. Verify all links work
4. Commit changes

### Document Naming Convention

```
[CATEGORY]_[TOPIC]_[DATE].md

Examples:
- MYCOBRAIN_STATUS_UPDATE_JAN_16_2026.md
- SECURITY_AUDIT_JAN17_2026.md
- SCALING_PLAN_90_DAYS.md
```

---

**END OF MASTER DOCUMENT INDEX**

*This index is the central reference for all Mycosoft documentation.*
