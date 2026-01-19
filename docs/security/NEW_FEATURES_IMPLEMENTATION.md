# Mycosoft SOC - New Features Implementation

**Version:** 2.1.0  
**Implementation Date:** January 18, 2026  
**Status:** ✅ COMPLETE

---

## Overview

This document describes the 6 critical features that have been implemented to make the Mycosoft Security Operations Center production-ready.

---

## Feature 1: Database Persistence

### File: `lib/security/database.ts`

### Description
Provides persistent storage for security events, incidents, audit logs, scan results, and playbook executions using Supabase with in-memory fallback.

### Key Functions

| Function | Description |
|----------|-------------|
| `createSecurityEvent()` | Store a new security event |
| `getSecurityEvents()` | Retrieve events with filters |
| `getEventStats()` | Get event statistics |
| `createIncident()` | Create a new incident |
| `getIncidents()` | Retrieve incidents |
| `updateIncident()` | Update incident status/details |
| `createAuditLog()` | Log audit trail entries |
| `getAuditLogs()` | Retrieve audit logs |
| `createScanResult()` | Store scan results |
| `getScanResults()` | Retrieve scan history |
| `createPlaybookExecution()` | Log playbook execution |
| `getPlaybookExecutions()` | Get execution history |

### Data Types

```typescript
interface SecurityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  source_ip: string | null;
  destination_ip: string | null;
  description: string;
  geo_location: GeoLocation | null;
  metadata: Record<string, unknown>;
  resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
}

interface Incident {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: 'open' | 'investigating' | 'contained' | 'resolved' | 'closed';
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  events: string[];
  tags: string[];
  timeline: IncidentTimelineEntry[];
}
```

### Usage

```typescript
import { createSecurityEvent, getSecurityEvents } from '@/lib/security/database';

// Create event
const event = await createSecurityEvent({
  timestamp: new Date().toISOString(),
  event_type: 'brute_force',
  severity: 'high',
  source_ip: '192.168.0.100',
  destination_ip: '192.168.0.1',
  description: 'Multiple failed login attempts detected',
  geo_location: null,
  metadata: { attempt_count: 15 },
  resolved: false,
  resolved_at: null,
  resolved_by: null,
});

// Query events
const events = await getSecurityEvents({
  limit: 50,
  severity: 'high',
  since: '2026-01-18T00:00:00Z',
});
```

---

## Feature 2: Email Alert System

### File: `lib/security/email-alerts.ts`

### Description
Multi-provider email alerting system supporting Resend, SendGrid, and console fallback. Includes HTML templates and severity-based routing.

### Supported Providers

| Provider | Environment Variable | Status |
|----------|---------------------|--------|
| Resend | `RESEND_API_KEY` | Ready |
| SendGrid | `SENDGRID_API_KEY` | Ready |
| Console | (default) | Active (dev mode) |

### Key Functions

| Function | Description |
|----------|-------------|
| `sendEmailAlert()` | Send generic email alert |
| `sendSecurityEventAlert()` | Send security event notification |
| `sendIncidentAlert()` | Send incident notification |
| `sendPlaybookAlert()` | Send playbook execution notification |
| `sendDailyDigest()` | Send daily security digest |
| `getEmailProviderStatus()` | Check email configuration |

### Email Templates

1. **Security Event** - For security events (medium+ severity)
2. **Incident Created** - For new incidents
3. **Playbook Executed** - For playbook completions
4. **Daily Digest** - Summary of security activity

### Usage

```typescript
import { sendSecurityEventAlert, sendIncidentAlert } from '@/lib/security/email-alerts';

// Send security event alert (only for medium+ severity)
await sendSecurityEventAlert({
  event_type: 'brute_force',
  severity: 'high',
  description: 'Brute force attack from 192.168.0.100',
  source_ip: '192.168.0.100',
});

// Send incident alert
await sendIncidentAlert({
  title: 'Critical: Data Exfiltration Detected',
  description: 'Large data transfer to unknown IP',
  severity: 'critical',
  status: 'open',
  assigned_to: 'Morgan',
});
```

---

## Feature 3: Real-Time WebSocket Alerts

### Files: 
- `lib/security/websocket-alerts.ts`
- `app/api/security/alerts/stream/route.ts`

### Description
Real-time alert broadcasting using Server-Sent Events (SSE). Supports filtering by severity and type, browser notifications, and audio alerts.

### Key Components

| Component | Description |
|-----------|-------------|
| `AlertManager` | Singleton that manages subscribers and broadcasts |
| `createAlertStream()` | Creates SSE stream for API route |
| `broadcastSecurityEvent()` | Broadcast security event |
| `broadcastIncidentAlert()` | Broadcast incident update |
| `broadcastPlaybookAlert()` | Broadcast playbook status |
| `broadcastScanAlert()` | Broadcast scan updates |

### Alert Types

```typescript
interface RealTimeAlert {
  id: string;
  timestamp: string;
  type: 'security_event' | 'incident' | 'playbook' | 'scan' | 'system';
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  data?: Record<string, unknown>;
  requiresAction?: boolean;
  actionUrl?: string;
}
```

### SSE Endpoint

```
GET /api/security/alerts/stream
Query Parameters:
  - severities: comma-separated list (e.g., "high,critical")
  - types: comma-separated list (e.g., "security_event,incident")
```

### Client-Side Usage

```typescript
// Connect to SSE stream
const eventSource = new EventSource('/api/security/alerts/stream?severities=high,critical');

eventSource.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  if (alert.type !== 'ping') {
    console.log('New alert:', alert);
    // Show notification, play sound, etc.
  }
};
```

### Browser Notifications

```typescript
import { requestNotificationPermission, showBrowserNotification, playAlertSound } from '@/lib/security/websocket-alerts';

// Request permission
await requestNotificationPermission();

// When alert received
showBrowserNotification(alert);
playAlertSound(alert.severity);
```

---

## Feature 4: Automated Response Playbook Engine

### File: `lib/security/playbook-engine.ts`

### Description
Full playbook execution engine with trigger matching, action execution, rate limiting, cooldowns, and human approval workflows.

### Built-in Playbooks

| Playbook | Trigger | Actions |
|----------|---------|---------|
| Brute Force Response | `brute_force`, 5+ attempts | Block IP, Send Alert, Create Incident |
| Port Scan Response | `port_scan`, medium+ | Enable Logging, Send Alert |
| Geographic Violation | `geo_violation` | Block IP (1 week), Alert |
| Malware Detection | `malware_detected` | Quarantine, Alert, Incident, Scan (requires approval) |
| Suspicious Traffic | `suspicious_traffic` | Enhanced Logging, Alert |

### Action Types

| Action | Description |
|--------|-------------|
| `block_ip` | Block IP via UniFi (TODO: full integration) |
| `quarantine_device` | Move to VLAN 99 (requires approval) |
| `send_alert` | Broadcast real-time alert |
| `create_incident` | Create incident in database |
| `enable_logging` | Enable enhanced logging |
| `run_scan` | Queue network scan |
| `webhook` | Call external webhook |
| `log` | Log to console |

### Key Functions

| Function | Description |
|----------|-------------|
| `processEvent()` | Match event to playbooks and execute |
| `executePlaybook()` | Execute a specific playbook |
| `getPlaybooks()` | Get playbook definitions |
| `getPendingApprovals()` | Get playbooks awaiting approval |
| `approvePlaybook()` | Approve pending playbook |
| `rejectPlaybook()` | Reject pending playbook |
| `triggerPlaybookManually()` | Manual trigger |

### Playbook Structure

```typescript
interface Playbook {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: {
    event_type: string | string[];
    severity_min: 'info' | 'low' | 'medium' | 'high' | 'critical';
    conditions?: PlaybookCondition[];
  };
  actions: PlaybookAction[];
  requires_approval: boolean;
  approval_timeout_minutes: number;
  cooldown_minutes: number;
  max_executions_per_hour: number;
}
```

### Usage

```typescript
import { processEvent, approvePlaybook } from '@/lib/security/playbook-engine';

// Automatic processing
await processEvent({
  id: 'evt-123',
  event_type: 'brute_force',
  severity: 'high',
  source_ip: '192.168.0.100',
  metadata: { attempt_count: 15 },
});

// Manual approval
await approvePlaybook('approval-abc123', 'morgan');
```

---

## Feature 5: Real Network Scanning

### File: `lib/security/network-scanner.ts`

### Description
JavaScript-based network scanner with port scanning, service detection, and vulnerability checks. Uses fetch for HTTP ports and queues for batch processing.

### Scan Types

| Type | Description | Ports |
|------|-------------|-------|
| `ping` | Host discovery | N/A |
| `syn` | TCP port scan | Common ports (27) |
| `version` | Service detection | Common ports |
| `vulnerability` | Vuln assessment | Common ports |
| `full` | Complete scan | All common ports |

### Key Functions

| Function | Description |
|----------|-------------|
| `queueScan()` | Queue a new scan |
| `getScanStatus()` | Check scan status |
| `getQueuedScans()` | Get all queued scans |
| `cancelScan()` | Cancel queued scan |
| `quickLocalScan()` | Scan localhost |
| `scanLocalNetwork()` | Scan 192.168.0.0/24 |

### Vulnerability Checks

| Port | Service | Vulnerability |
|------|---------|---------------|
| 21 | FTP | Clear-text credentials |
| 23 | Telnet | Unencrypted access |
| 3389 | RDP | Remote access exposed |
| 6379 | Redis | Unauthenticated access |
| 27017 | MongoDB | Unauthenticated access |

### Usage

```typescript
import { queueScan, getScanStatus } from '@/lib/security/network-scanner';

// Queue a scan
const scanId = await queueScan({
  target: '192.168.0.0/24',
  scan_type: 'vulnerability',
  triggered_by: 'admin',
});

// Check status
const status = getScanStatus(scanId);
console.log(status); // { status: 'running', ... }
```

### API Endpoints

```
POST /api/security
{ "action": "queue_scan", "target": "192.168.0.0/24", "scan_type": "syn" }

GET /api/security?action=scan-queue
GET /api/security?action=scan-results
```

---

## Feature 6: Suricata IDS Integration

### File: `lib/security/suricata-ids.ts`

### Description
Suricata IDS integration with eve.json log parsing, Redis subscription, and mock event generation for testing.

### Features

- Parse Suricata eve.json alerts
- Map Suricata severity to SOC severity
- Track statistics (top signatures, IPs, categories)
- Trigger playbooks on IDS alerts
- Send email alerts for high+ severity
- Real-time broadcasting

### Key Functions

| Function | Description |
|----------|-------------|
| `processSuricataEvent()` | Process a single Suricata event |
| `getIDSStats()` | Get IDS statistics |
| `getRecentAlerts()` | Get recent IDS alerts |
| `initializeIDS()` | Start IDS monitoring |
| `shutdownIDS()` | Stop IDS monitoring |
| `testWithMockEvent()` | Generate test event |
| `isIDSConnected()` | Check connection status |

### IDS Statistics

```typescript
interface IDSStats {
  alerts_total: number;
  alerts_last_hour: number;
  alerts_last_day: number;
  top_signatures: { signature: string; count: number }[];
  top_source_ips: { ip: string; count: number }[];
  top_categories: { category: string; count: number }[];
  severity_distribution: Record<number, number>;
  connected: boolean;
  last_event_time: string | null;
}
```

### Usage

```typescript
import { initializeIDS, getIDSStats, testWithMockEvent } from '@/lib/security/suricata-ids';

// Initialize with mock events for testing
await initializeIDS({ enableMockEvents: true });

// Get statistics
const stats = getIDSStats();
console.log(`Total alerts: ${stats.alerts_total}`);

// Generate test event
const event = await testWithMockEvent();
```

### API Endpoints

```
GET /api/security?action=ids-status
GET /api/security?action=ids-stats
GET /api/security?action=ids-alerts&limit=100

POST /api/security
{ "action": "test_ids" }

POST /api/security
{ "action": "init_ids", "enable_mock": true }
```

---

## New API Endpoints Summary

### GET Endpoints

| Endpoint | Description |
|----------|-------------|
| `?action=db-events` | Database-backed events |
| `?action=event-stats` | Event statistics |
| `?action=incidents` | Incident list |
| `?action=playbook-definitions` | Enhanced playbook list |
| `?action=playbook-executions` | Execution history |
| `?action=pending-approvals` | Awaiting approval |
| `?action=scan-queue` | Queued scans |
| `?action=scan-results` | Scan results |
| `?action=ids-status` | IDS connection status |
| `?action=ids-stats` | IDS statistics |
| `?action=ids-alerts` | Recent IDS alerts |
| `?action=audit-logs` | Audit trail |
| `?action=realtime-stats` | WebSocket stats |
| `?action=email-status` | Email provider status |

### POST Actions

| Action | Description |
|--------|-------------|
| `db_create_event` | Create event in database |
| `create_incident` | Create incident |
| `update_incident` | Update incident |
| `queue_scan` | Queue network scan |
| `approve_playbook` | Approve pending playbook |
| `reject_playbook` | Reject pending playbook |
| `trigger_playbook_manual` | Manual trigger |
| `test_ids` | Generate test IDS event |
| `init_ids` | Initialize IDS monitoring |
| `send_test_email` | Send test email |
| `create_audit_log` | Create audit entry |

---

## Environment Variables

Add these to `.env.local`:

```bash
# Email (optional - falls back to console)
RESEND_API_KEY=re_xxxxxxxxxxxx
# OR
SENDGRID_API_KEY=SG.xxxxxxxxxxxx

# Email sender
EMAIL_FROM=security@mycosoft.com

# Supabase (for persistence)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# IDS (optional)
SURICATA_EVE_PATH=/var/log/suricata/eve.json
REDIS_URL=redis://localhost:6379
```

---

## Database Schema (Supabase)

```sql
-- Security Events
CREATE TABLE security_events (
  id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  source_ip INET,
  destination_ip INET,
  description TEXT,
  geo_location JSONB,
  metadata JSONB DEFAULT '{}',
  resolved BOOLEAN DEFAULT false,
  resolved_at TIMESTAMPTZ,
  resolved_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Incidents
CREATE TABLE incidents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  assigned_to TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  events TEXT[] DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  timeline JSONB DEFAULT '[]'
);

-- Audit Logs
CREATE TABLE audit_logs (
  id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  action TEXT NOT NULL,
  actor TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details JSONB DEFAULT '{}',
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scan Results
CREATE TABLE scan_results (
  id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  scan_type TEXT NOT NULL,
  target TEXT NOT NULL,
  status TEXT NOT NULL,
  results JSONB DEFAULT '{}',
  vulnerabilities_found INTEGER DEFAULT 0,
  hosts_discovered INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Playbook Executions
CREATE TABLE playbook_executions (
  id TEXT PRIMARY KEY,
  playbook_id TEXT NOT NULL,
  playbook_name TEXT NOT NULL,
  triggered_by TEXT NOT NULL,
  trigger_event_id TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  actions_executed JSONB DEFAULT '[]',
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_timestamp ON security_events(timestamp DESC);
CREATE INDEX idx_events_severity ON security_events(severity);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
```

---

## File Structure

```
lib/security/
├── index.ts                 # Central exports
├── database.ts              # Database persistence (NEW)
├── email-alerts.ts          # Email alerting (NEW)
├── websocket-alerts.ts      # Real-time alerts (NEW)
├── playbook-engine.ts       # Playbook execution (NEW)
├── network-scanner.ts       # Network scanning (NEW)
├── suricata-ids.ts          # Suricata IDS (NEW)
├── threat-intel.ts          # Threat intelligence
├── playbooks.ts             # Legacy playbooks
├── scanner.ts               # Legacy scanner
├── alerting.ts              # Legacy alerting
├── myca-sec.ts              # AI integration
├── anomaly-detector.ts      # Anomaly detection
└── recovery.ts              # Recovery automation

app/api/security/
├── route.ts                 # Main security API (ENHANCED)
└── alerts/
    └── stream/
        └── route.ts         # SSE alerts endpoint (NEW)
```

---

**Document Control:**
- Created: January 18, 2026
- Author: Mycosoft Security Team
- Status: Implementation Complete
