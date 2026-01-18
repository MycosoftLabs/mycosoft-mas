# Mycosoft Security Operations Center (SOC)

**Version**: 1.0.0  
**Date**: 2026-01-17  
**Status**: 🟢 ACTIVE - 24/7 MONITORING  
**Classification**: CONFIDENTIAL - Internal Only

---

## 🛡️ Executive Summary

The Mycosoft Security Operations Center (SOC) provides comprehensive 24/7 security monitoring for the Mycosoft infrastructure. It integrates with the UniFi Dream Machine to detect, analyze, and respond to security threats in real-time.

### Key Features

- **Real-time Network Monitoring** via UniFi API integration
- **Geo-IP Threat Detection** - Flag traffic from unauthorized countries
- **Authorized User Tracking** - Known user location verification
- **Automatic Threat Response** - Auto-block critical threats
- **Multi-channel Alerting** - Slack, Email, Dashboard notifications
- **24/7 Automated Monitoring** via n8n workflows

---

## 👥 Authorized Users

The following users are authorized to access Mycosoft systems:

| User | Role | Primary Location | Additional Locations | Mobile | VPN |
|------|------|------------------|---------------------|--------|-----|
| **Morgan** | Super Admin | Chula Vista, CA | - | ✅ | ✅ |
| **Chris** | Admin | Portland, OR | - | ✅ | ✅ |
| **Garrett** | Admin | Pasadena, CA | Chula Vista (visiting) | ✅ | ✅ |
| **RJ** | Admin | Chula Vista, CA | Little Italy, San Diego | ✅ | ✅ |
| **Beto** | Admin | Chula Vista, CA | Alberta, Canada | ✅ | ✅ |

### Location Verification

Each authorized user has registered locations with GPS coordinates and radius for verification:

```
Morgan:    Chula Vista, CA     (32.6401, -117.0842)  15km radius
Chris:     Portland, OR        (45.5152, -122.6784)  30km radius
Garrett:   Pasadena, CA        (34.1478, -118.1445)  30km radius
           Chula Vista, CA     (32.6401, -117.0842)  15km radius
RJ:        Chula Vista, CA     (32.6401, -117.0842)  15km radius
           Little Italy, SD    (32.7226, -117.1698)  10km radius
Beto:      Chula Vista, CA     (32.6401, -117.0842)  15km radius
           Alberta, Canada     (53.5461, -113.4938)  200km radius
```

---

## 🌍 Geographic Access Policy

### Allowed Countries

| Code | Country | Status |
|------|---------|--------|
| **US** | United States | ✅ Allowed |
| **CA** | Canada | ✅ Allowed (Beto) |

### High-Risk Countries (Auto-Block)

| Code | Country | Action |
|------|---------|--------|
| CN | China | 🔴 BLOCK + ALERT |
| RU | Russia | 🔴 BLOCK + ALERT |
| KP | North Korea | 🔴 BLOCK + ALERT |
| IR | Iran | 🔴 BLOCK + ALERT |
| BY | Belarus | 🔴 BLOCK + ALERT |
| VE | Venezuela | 🔴 BLOCK + ALERT |
| SY | Syria | 🔴 BLOCK + ALERT |
| CU | Cuba | 🔴 BLOCK + ALERT |

### Trusted External Services

Traffic to/from these services is whitelisted:

| Service | Domain | Purpose |
|---------|--------|---------|
| Anthropic | anthropic.com | Claude AI API |
| OpenAI | openai.com | GPT API |
| Supabase | supabase.co | Database/Auth |
| Cloudflare | cloudflare.com | CDN/Security |
| Google APIs | googleapis.com | Maps, Earth Engine |
| ElevenLabs | elevenlabs.io | Voice synthesis |
| GitHub | github.com | Code repository |
| iNaturalist | inaturalist.org | Species data |
| GBIF | gbif.org | Biodiversity data |
| OpenSky | opensky-network.org | Aviation tracking |
| AISStream | aisstream.io | Maritime tracking |
| FlightRadar24 | flightradar24.com | Flight tracking |
| Space-Track | space-track.org | Satellite tracking |

---

## 🚨 Threat Detection Rules

### Rule 001: Non-US/CA Traffic
- **Severity**: MEDIUM
- **Condition**: Country NOT IN [US, CA]
- **Action**: ALERT
- **Exception**: Matches authorized user locations

### Rule 002: High-Risk Country Traffic
- **Severity**: CRITICAL
- **Condition**: Country IN [CN, RU, KP, IR, BY, VE, SY, CU]
- **Action**: BLOCK + ALERT

### Rule 003: Unknown IP Access
- **Severity**: HIGH
- **Condition**: IP not matching known user locations
- **Action**: ALERT

### Rule 004: Brute Force Detection
- **Severity**: CRITICAL
- **Condition**: >5 failed logins per minute
- **Action**: BLOCK + ALERT

### Rule 005: Port Scan Detection
- **Severity**: HIGH
- **Condition**: >20 unique ports per minute
- **Action**: BLOCK + ALERT

### Rule 006: Data Exfiltration
- **Severity**: CRITICAL
- **Condition**: >500MB outbound per hour
- **Action**: ALERT

### Rule 007: Off-Hours Access
- **Severity**: MEDIUM
- **Condition**: Access outside business hours from unknown IP
- **Action**: ALERT

### Rule 008: TOR Exit Node
- **Severity**: HIGH
- **Condition**: IP is known TOR exit node
- **Action**: BLOCK + ALERT

### Rule 009: VPN Detection
- **Severity**: INFO
- **Condition**: VPN/Proxy/Hosting provider detected
- **Action**: LOG

### Rule 010: New Device Connection
- **Severity**: LOW
- **Condition**: Device first seen within 1 hour
- **Action**: ALERT

---

## 📊 Security Dashboard

Access the Security Operations Dashboard at:

```
https://mycosoft.com/dashboard/soc
```

### Dashboard Features

1. **Threat Level Indicator** - Current security posture (Low/Elevated/High/Critical)
2. **Real-time Event Feed** - Live security events
3. **Authorized User Status** - User locations and activity
4. **Geo-IP Lookup Tool** - Investigate IP addresses
5. **Top Threat Sources** - Most active threat IPs
6. **Country Distribution** - Geographic threat analysis
7. **One-Click Blocking** - Instantly block malicious IPs

---

## 🔧 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MYCOSOFT SECURITY OPERATIONS CENTER                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │   UniFi UDM     │────▶│ Security Monitor │────▶│  Event Store    │       │
│  │  192.168.0.1    │     │    (Python)      │     │  (PostgreSQL)   │       │
│  │                 │     │                  │     │                 │       │
│  │ - Clients       │     │ - Geo-IP Lookup  │     │ - Security Logs │       │
│  │ - IDS/IPS       │     │ - Threat Detect  │     │ - Audit Trail   │       │
│  │ - Firewall      │     │ - Auto-Block     │     │ - Retention     │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│           │                       │                       │                 │
│           │                       ▼                       │                 │
│           │              ┌─────────────────┐              │                 │
│           │              │  Alert Manager  │              │                 │
│           │              └────────┬────────┘              │                 │
│           │                       │                       │                 │
│           │         ┌─────────────┼─────────────┐         │                 │
│           │         ▼             ▼             ▼         │                 │
│           │  ┌───────────┐ ┌───────────┐ ┌───────────┐    │                 │
│           │  │   Slack   │ │   Email   │ │ Dashboard │    │                 │
│           │  │  Channel  │ │  Alerts   │ │    UI     │    │                 │
│           │  └───────────┘ └───────────┘ └───────────┘    │                 │
│           │                                               │                 │
│           └───────────────────────────────────────────────┘                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         n8n AUTOMATION                               │   │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                 │   │
│  │  │ Every 30s  │───▶│ Get Clients│───▶│ Analyze    │                 │   │
│  │  │  Trigger   │    │ + IDS Data │    │ Threats    │                 │   │
│  │  └────────────┘    └────────────┘    └──────┬─────┘                 │   │
│  │                                              │                       │   │
│  │                              ┌───────────────┼───────────────┐       │   │
│  │                              ▼               ▼               ▼       │   │
│  │                       ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │                       │Auto-Block │  │  Alert    │  │  Log to   │   │   │
│  │                       │ Critical  │  │  Slack    │  │  Dashboard│   │   │
│  │                       └───────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

### Security API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/security` | GET | Dashboard overview |
| `/api/security?action=status` | GET | Security status |
| `/api/security?action=users` | GET | Authorized users |
| `/api/security?action=events` | GET | Security events |
| `/api/security?action=threats` | GET | Threat summary |
| `/api/security?action=geo-lookup&ip=X` | GET | Geo-IP lookup |
| `/api/security` | POST | Report event, block/unblock IP |

### Example: Report Security Event

```bash
curl -X POST https://mycosoft.com/api/security \
  -H "Content-Type: application/json" \
  -d '{
    "action": "report_event",
    "event_type": "suspicious_access",
    "severity": "high",
    "source_ip": "203.0.113.42",
    "description": "Suspicious access pattern detected"
  }'
```

### Example: Block IP

```bash
curl -X POST https://mycosoft.com/api/security \
  -H "Content-Type: application/json" \
  -d '{
    "action": "block_ip",
    "ip": "203.0.113.42",
    "reason": "Confirmed malicious activity"
  }'
```

---

## 🚀 Deployment

### Prerequisites

1. UniFi Dream Machine with API access enabled
2. Docker and Docker Compose
3. Slack webhook for alerts (optional)
4. MaxMind GeoIP database (optional, free tier available)

### Configuration

1. **Set environment variables**:

```bash
export UNIFI_HOST=192.168.0.1
export UNIFI_API_KEY=your-api-key
export SLACK_SECURITY_WEBHOOK=https://hooks.slack.com/...
```

2. **Deploy security service**:

```bash
cd website/services/security
docker-compose -f docker-compose.security.yml up -d
```

3. **Import n8n workflow**:
   - Open n8n at http://localhost:5678
   - Import `n8n/security-monitoring-workflow.json`
   - Configure credentials for UniFi API
   - Activate the workflow

### Verify Deployment

```bash
# Check service health
curl http://localhost:3000/api/security?action=status

# Expected response:
{
  "status": "active",
  "threat_level": "low",
  "monitoring_enabled": true,
  ...
}
```

---

## 📋 Operational Procedures

### Daily Checklist

- [ ] Review SOC dashboard for overnight events
- [ ] Check threat level indicator
- [ ] Review any unacknowledged alerts
- [ ] Verify authorized user locations match activity

### Weekly Checklist

- [ ] Review blocked IP list
- [ ] Analyze country distribution of events
- [ ] Update authorized user locations if needed
- [ ] Review top threat sources

### Monthly Checklist

- [ ] Rotate API keys
- [ ] Update GeoIP database
- [ ] Review and update threat detection rules
- [ ] Test alert channels (Slack, email)
- [ ] Full security audit

---

## 🚨 Incident Response

### Severity Levels

| Level | Response Time | Actions |
|-------|--------------|---------|
| **CRITICAL** | Immediate | Auto-block, all channels alert, investigate |
| **HIGH** | 1 hour | Alert, manual review, possible block |
| **MEDIUM** | 4 hours | Alert, log, monitor |
| **LOW** | 24 hours | Log, review in daily check |
| **INFO** | N/A | Log only |

### Response Procedures

#### Critical Threat Detected

1. **Automatic Response**:
   - IP is auto-blocked via UniFi API
   - Slack alert sent immediately
   - Event logged to dashboard

2. **Manual Investigation**:
   - Access SOC dashboard
   - Review event details and geo-location
   - Verify not a false positive (authorized user on VPN)
   - If confirmed threat: keep blocked
   - If false positive: unblock and add exception

3. **Post-Incident**:
   - Document incident
   - Update rules if needed
   - Review similar events

---

## 🔗 Related Documentation

| Document | Path | Description |
|----------|------|-------------|
| Security Audit | `docs/SECURITY_AUDIT_JAN17_2026.md` | Latest security audit |
| Security Hardening | `docs/setup/SECURITY_HARDENING_GUIDE.md` | Security best practices |
| VLAN Security | `docs/infrastructure/VLAN_SECURITY.md` | Network segmentation |
| UniFi Integration | `docs/setup/UBIQUITI_NETWORK_INTEGRATION.md` | UniFi API setup |

---

## 📁 File Locations

| File | Purpose |
|------|---------|
| `config/security/authorized-users.json` | Authorized users and locations |
| `config/security/security-config.json` | SOC configuration |
| `services/security/unifi_security_monitor.py` | Main monitoring service |
| `app/api/security/route.ts` | Security API endpoints |
| `app/dashboard/soc/page.tsx` | SOC Dashboard UI |
| `n8n/security-monitoring-workflow.json` | n8n automation workflow |

---

## 🔐 Security Agents

The SOC integrates with these security agents:

| Agent ID | Name | Status | Description |
|----------|------|--------|-------------|
| 170 | auth | Active | Authentication |
| 171 | authorization | Active | Access control |
| **172** | **watchdog** | **Active** | Continuous threat monitoring |
| **173** | **hunter** | **Active** | Proactive threat hunting |
| **174** | **guardian** | **Active** | System protection |
| 175 | compliance | Active | Regulatory compliance |
| 176 | audit | Active | Security audit logs |
| **177** | **incident-response** | **Active** | Automated incident handling |

---

## 📞 Contact

### Security Escalation Chain

1. **Dashboard Alert** - Immediate (all events)
2. **Slack #security-alerts** - 5 minutes (medium+)
3. **Email** - 15 minutes (high+)
4. **SMS** - 30 minutes (critical only)

### Emergency Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| Super Admin | Morgan | Final authority |
| System Admin | [TBD] | Infrastructure |
| Security Lead | [TBD] | Incident coordination |

---

*Document maintained by Mycosoft Security Team*  
*Last Updated: 2026-01-17*
