# Mycosoft Security Operations Center (SOC)
## Complete Technical Documentation

**Version:** 2.0.0  
**Last Updated:** January 18, 2026  
**Classification:** INTERNAL USE ONLY  
**Author:** Mycosoft Security Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Capabilities Overview](#capabilities-overview)
4. [Security Protocols](#security-protocols)
5. [Component Documentation](#component-documentation)
6. [API Reference](#api-reference)
7. [Data Flows](#data-flows)
8. [Integration Points](#integration-points)

---

## Executive Summary

The Mycosoft Security Operations Center (SOC) is a comprehensive, 24/7 network security monitoring and incident response platform designed to protect the Mycosoft infrastructure. Built on Next.js with real-time UniFi Dream Machine Pro integration, the SOC provides:

- **Real-time network monitoring** via UniFi API
- **Threat intelligence** from multiple sources (AbuseIPDB, VirusTotal, Tor exit nodes)
- **Automated incident response** with playbook execution
- **Red Team capabilities** for penetration testing
- **Compliance tracking** against NIST CSF framework
- **Geo-IP monitoring** with US-only access restrictions

### Key Metrics
- **Uptime Target:** 99.9%
- **Alert Response Time:** < 5 minutes for critical
- **Authorized Users:** 5 (Morgan, Chris, Garrett, RJ, Beto)
- **Allowed Countries:** United States only
- **Network Coverage:** Full UniFi Dream Machine Pro ecosystem

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MYCOSOFT SOC v2.0                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   UniFi     │  │   Threat    │  │   Suricata  │  │   Nmap      │         │
│  │ Dream       │  │   Intel     │  │   IDS/IPS   │  │   Scanner   │         │
│  │ Machine Pro │  │   Service   │  │             │  │             │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                │                 │
│         └────────────────┼────────────────┼────────────────┘                 │
│                          │                │                                  │
│                    ┌─────▼────────────────▼─────┐                           │
│                    │         REDIS              │                           │
│                    │   Event Queue & Cache      │                           │
│                    └─────────────┬──────────────┘                           │
│                                  │                                          │
│                    ┌─────────────▼──────────────┐                           │
│                    │     Next.js API Layer      │                           │
│                    │  /api/security             │                           │
│                    │  /api/unifi                │                           │
│                    │  /api/pentest              │                           │
│                    └─────────────┬──────────────┘                           │
│                                  │                                          │
│  ┌───────────────────────────────┼───────────────────────────────────────┐  │
│  │                    SOC Dashboard UI                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │ Security │ │ Network  │ │Incidents │ │ Red Team │ │Compliance│    │  │
│  │  │ Overview │ │ Monitor  │ │ Mgmt     │ │ Ops      │ │ Audit    │    │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 15, React 18, Tailwind CSS | SOC Dashboard UI |
| API | Next.js API Routes | RESTful endpoints |
| Cache/Queue | Redis 7.0 | Event queue, caching |
| IDS/IPS | Suricata 7.0 | Network intrusion detection |
| Scanning | Nmap, Masscan | Network/vulnerability scanning |
| Network | UniFi Dream Machine Pro | Gateway, firewall, WiFi |
| Threat Intel | AbuseIPDB, VirusTotal | IP reputation |

### Network Topology

```
Internet
    │
    ▼
┌─────────────────────────────────┐
│   UniFi Dream Machine Pro Max   │
│   192.168.1.141 (WAN)           │
│   Wyyerd Fiber Connection       │
└─────────────┬───────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌────────────┐    ┌────────────┐
│WHITE U7 Pro│    │BLACK U7 Pro│
│   XGS      │    │   XGS      │
│192.168.0.68│    │192.168.0.183│
└────────────┘    └────────────┘
        │
        ▼
┌─────────────────────────────────┐
│       Internal Network          │
│  192.168.0.0/24                 │
│                                 │
│  • UNAS-Pro (192.168.0.105)     │
│  • MycoComp (192.168.0.172)     │
│  • ubuntu-server (192.168.0.187)│
│  • Proxmox VM Host              │
└─────────────────────────────────┘
```

---

## Capabilities Overview

### 1. Real-Time Network Monitoring

| Capability | Description | Data Source |
|------------|-------------|-------------|
| WAN Status | Live WAN IP and ISP monitoring | UniFi API |
| Throughput | Real-time up/down bandwidth | UniFi API |
| Client Tracking | Connected clients with details | UniFi API |
| Device Health | Network device status | UniFi API |
| Alarm Monitoring | Real-time security alerts | UniFi API |
| Traffic Analysis | Top destinations, clients, apps | UniFi API |

### 2. Threat Intelligence

| Source | Data Provided | Update Frequency |
|--------|---------------|------------------|
| AbuseIPDB | IP abuse reports, confidence scores | Per-query (cached 1hr) |
| VirusTotal | Malware associations, threat types | Per-query (cached 1hr) |
| Tor Exit Nodes | Anonymous network detection | Every 6 hours |
| Internal DB | Custom threat tracking | Real-time |

### 3. Geo-IP Security

| Feature | Configuration |
|---------|---------------|
| Allowed Countries | United States (US) only |
| High-Risk Countries | CN, RU, KP, IR, BY, VE, SY, CU |
| VPN/Proxy Detection | Enabled |
| Hosting Detection | Enabled |

### 4. Intrusion Detection

| System | Capabilities |
|--------|--------------|
| Suricata IDS | Network traffic analysis, signature-based detection |
| Anomaly Detection | Baseline deviation alerting |
| Port Scan Detection | Automated scan pattern recognition |
| Brute Force Detection | Failed auth attempt monitoring |

### 5. Incident Response

| Phase | Automation Level |
|-------|-----------------|
| Detection | Fully automated |
| Classification | Automated with AI assistance |
| Containment | Semi-automated (playbook-driven) |
| Eradication | Human-supervised |
| Recovery | Playbook-driven |
| Lessons Learned | Manual |

### 6. Red Team / Penetration Testing

| Tool | Purpose | Status |
|------|---------|--------|
| Nmap | Network discovery, port scanning | Operational |
| Masscan | High-speed port scanning | Planned |
| Nikto | Web vulnerability scanning | Planned |
| SQLMap | SQL injection testing | Planned |
| Custom Scripts | Tailored assessments | Development |

### 7. Compliance & Audit

| Framework | Coverage | Status |
|-----------|----------|--------|
| NIST CSF 1.1 | 11 controls | 95% compliant |
| ISO 27001 | Partial | In progress |
| SOC 2 Type II | Planned | Q2 2026 |

---

## Security Protocols

### Authentication & Authorization

1. **API Authentication**
   - UniFi API: API Key (`X-API-Key` header)
   - Internal APIs: Session-based (NextAuth)
   - External APIs: API keys stored in environment variables

2. **User Authorization**
   ```json
   {
     "roles": ["super_admin", "admin", "analyst", "viewer"],
     "access_levels": ["full", "limited", "read_only"]
   }
   ```

3. **Geographic Access Control**
   - All access restricted to US-based IPs
   - VPN access allowed for authorized users
   - Mobile access enabled with MFA

### Data Protection

1. **In Transit**
   - HTTPS/TLS 1.3 for all external communications
   - Self-signed certificates for internal UniFi API (SSL verification bypassed)

2. **At Rest**
   - Environment variables for secrets
   - Redis data encrypted at rest
   - Suricata logs stored locally

3. **Retention**
   - Security events: 90 days
   - Audit logs: 1 year
   - Compliance reports: 7 years

### Incident Classification

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| Critical | < 5 minutes | Immediate page to Morgan |
| High | < 15 minutes | Email to all admins |
| Medium | < 1 hour | Dashboard alert |
| Low | < 24 hours | Logged only |
| Info | N/A | Logged only |

### Network Segmentation (VLAN Strategy)

| VLAN | ID | Purpose | Access |
|------|-----|---------|--------|
| Management | 1 | Network infrastructure | Admin only |
| Servers | 10 | Production servers | Limited |
| Workstations | 20 | Employee devices | Standard |
| IoT | 30 | Smart devices | Isolated |
| Guest | 40 | Guest WiFi | Internet only |
| Quarantine | 99 | Compromised devices | None |

---

## Component Documentation

### 1. Security Operations Center Dashboard

**Path:** `/security`

**Features:**
- Real-time threat level indicator
- Monitoring status display
- Event statistics (24h, critical, high)
- Unique IP counter
- Authorized user list
- IP lookup tool
- Recent events feed
- Security agent status
- Quick action links

**API Endpoints:**
- `GET /api/security?action=status` - System status
- `GET /api/security?action=users` - Authorized users
- `GET /api/security?action=events` - Recent events
- `GET /api/security?action=geo-lookup&ip=X.X.X.X` - IP lookup

### 2. Network Security Monitor

**Path:** `/security/network`

**Features:**
- UniFi Dream Machine Pro integration
- Live throughput monitoring
- Connected client list
- Network device status
- WiFi network overview
- Recent alarms display
- Traffic analysis
- Network topology view

**API Endpoints:**
- `GET /api/unifi?action=dashboard` - Full dashboard data
- `GET /api/unifi?action=devices` - Network devices
- `GET /api/unifi?action=clients` - Connected clients
- `GET /api/unifi?action=traffic` - Traffic statistics
- `GET /api/unifi?action=alarms` - Active alarms

### 3. Incident Management

**Path:** `/security/incidents`

**Features:**
- Incident list with status filters
- Severity classification
- Assignment tracking
- Status workflow (Open → Investigating → Contained → Resolved)
- Incident details view
- Timeline tracking
- Evidence attachment

**API Endpoints:**
- `GET /api/security?action=incidents` - List incidents
- `POST /api/security { action: "create_incident" }` - Create incident
- `POST /api/security { action: "resolve_incident" }` - Resolve incident

### 4. Red Team Operations

**Path:** `/security/redteam`

**Features:**
- Network scanner interface
- Scan type selection (Ping, SYN, Version, Vulnerability)
- Target network configuration
- Vulnerability tracking
- Attack simulation controls
- Scheduled scan management

**API Endpoints:**
- `POST /api/security { action: "run_scan" }` - Start scan
- `GET /api/security?action=scan` - Get scan results
- `GET /api/security?action=vulnerabilities` - Get vulnerabilities

### 5. Compliance & Audit

**Path:** `/security/compliance`

**Features:**
- Compliance score dashboard
- NIST control family browser
- Individual control status
- Evidence tracking
- Audit log viewer
- PDF report generation

**API Endpoints:**
- `GET /api/security?action=compliance-reports` - Get reports
- `POST /api/security { action: "generate_compliance_report" }` - Generate report

---

## API Reference

### Security API (`/api/security`)

#### GET Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `status` | System status | None |
| `users` | Authorized users | None |
| `events` | Recent security events | `limit`, `severity` |
| `geo-lookup` | IP geolocation | `ip` (required) |
| `incidents` | Incident list | `status`, `severity` |
| `scan` | Scan results | `scan_id` |
| `vulnerabilities` | Vulnerability list | `ip`, `severity` |
| `playbooks` | Response playbooks | None |
| `compliance-reports` | Compliance reports | None |

#### POST Actions

| Action | Description | Payload |
|--------|-------------|---------|
| `log_event` | Log security event | Event object |
| `create_incident` | Create incident | Incident object |
| `resolve_incident` | Resolve incident | `incident_id` |
| `run_scan` | Start network scan | `target`, `scan_type` |
| `trigger_playbook` | Execute playbook | `playbook_id`, `event_data` |
| `quarantine_device` | Quarantine device | `device_id` |

### UniFi API (`/api/unifi`)

#### GET Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `dashboard` | Full dashboard data | None |
| `devices` | Network devices | None |
| `clients` | Connected clients | None |
| `traffic` | Traffic statistics | None |
| `alarms` | Active alarms | `limit` |
| `topology` | Network topology | None |
| `wlans` | WiFi networks | None |

---

## Data Flows

### Event Processing Flow

```
┌─────────────────┐
│  Event Source   │
│  (UniFi/Suricata│
│   /Application) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Event Parser   │
│  (Normalize)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Queue    │
│  (security_     │
│   events)       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────────┐
│ Store │ │ Playbook  │
│ Event │ │ Matcher   │
└───────┘ └─────┬─────┘
                │
                ▼
         ┌──────────────┐
         │ Execute      │
         │ Playbook     │
         └──────────────┘
```

### Threat Intelligence Flow

```
┌─────────────────┐
│  IP Address     │
│  Input          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cache Check    │
│  (Redis)        │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Miss    │ Hit
    ▼         ▼
┌───────────┐ ┌────────────┐
│ Query     │ │ Return     │
│ External  │ │ Cached     │
│ APIs      │ │ Result     │
└─────┬─────┘ └────────────┘
      │
      ▼
┌─────────────────┐
│  Merge Results  │
│  Calculate Risk │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cache Result   │
│  (1 hour TTL)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Return to      │
│  Requester      │
└─────────────────┘
```

---

## Integration Points

### External Services

| Service | Purpose | Auth Method | Status |
|---------|---------|-------------|--------|
| UniFi Dream Machine | Network data | API Key | ✅ Active |
| AbuseIPDB | IP reputation | API Key | ✅ Active |
| VirusTotal | Threat analysis | API Key | ⚠️ Needs key |
| Cloudflare | WAF, DNS | API Token | Planned |
| Supabase | Database | Anon Key | ✅ Active |

### Internal Services

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| Redis | Cache/Queue | 6379 | Planned |
| Suricata | IDS | N/A | Planned |
| Nmap Scanner | Scanning | N/A | Planned |
| Threat Intel Service | Intel aggregation | 8100 | Planned |

---

## Appendices

### A. Authorized Users

| Name | Role | Locations | Access |
|------|------|-----------|--------|
| Morgan | super_admin | Chula Vista, CA | Full |
| Chris | admin | Portland, OR | Full |
| Garrett | admin | Pasadena, CA; Chula Vista, CA | Full |
| RJ | admin | Chula Vista, CA; San Diego, CA | Full |
| Beto | admin | Chula Vista, CA | Limited |

### B. Environment Variables

```bash
# UniFi Configuration
UNIFI_HOST=192.168.0.1
UNIFI_API_KEY=BfRgo4k9aS0-yo8BKqXpEtdo4k2jzM8k
UNIFI_SITE=default

# Threat Intelligence
ABUSEIPDB_API_KEY=<your-key>
VIRUSTOTAL_API_KEY=<your-key>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Suricata
SURICATA_LOG_PATH=/var/log/suricata/eve.json
```

### C. File Structure

```
website/
├── app/
│   ├── api/
│   │   ├── security/
│   │   │   └── route.ts          # Security API
│   │   ├── unifi/
│   │   │   └── route.ts          # UniFi API
│   │   └── pentest/
│   │       └── route.ts          # Pentest API
│   └── security/
│       ├── page.tsx              # SOC Dashboard
│       ├── network/
│       │   └── page.tsx          # Network Monitor
│       ├── incidents/
│       │   └── page.tsx          # Incident Management
│       ├── redteam/
│       │   └── page.tsx          # Red Team Ops
│       └── compliance/
│           └── page.tsx          # Compliance
├── lib/
│   └── security/
│       ├── threat-intel.ts       # Threat intelligence
│       ├── playbooks.ts          # Response playbooks
│       ├── scanner.ts            # Scanning tools
│       ├── alerting.ts           # Alert system
│       ├── myca-sec.ts           # AI engine
│       ├── anomaly-detector.ts   # Anomaly detection
│       └── recovery.ts           # Recovery automation
└── services/
    └── security/
        ├── docker-compose.security-tools.yml
        ├── nmap_scanner.py
        ├── threat_intel_service.py
        ├── suricata_parser.py
        └── event_processor.py
```

---

**Document Control:**
- Created: January 18, 2026
- Review Cycle: Monthly
- Next Review: February 18, 2026
- Owner: Morgan (super_admin)
