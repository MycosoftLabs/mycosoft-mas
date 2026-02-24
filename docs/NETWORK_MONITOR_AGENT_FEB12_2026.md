# Network Monitor Agent and Diagnostics

**Date**: February 12, 2026  
**Status**: Implemented  
**Priority**: High – DNS anomaly and network security monitoring

---

## Overview

The Network Monitor Agent runs topology, DNS, latency, connectivity, and vulnerability checks. It integrates with UniFi (Ubiquiti), Cloudflare, and system tools to detect DNS anomalies (hijacking, poisoning), unauthorized clients, and connectivity issues.

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| NetworkMonitorAgent | `mycosoft_mas/agents/network_monitor_agent.py` | MAS agent for periodic diagnostics |
| Network diagnostics service | `mycosoft_mas/services/network_diagnostics.py` | DNS, latency, connectivity, topology logic |
| Network API router | `mycosoft_mas/core/routers/network_api.py` | REST endpoints for diagnostics |
| UniFi client | `mycosoft_mas/integrations/unifi_client.py` | UniFi Dream Machine Pro API |
| Cloudflare DNS client | `mycosoft_mas/integrations/cloudflare_dns_client.py` | Cloudflare DNS records |
| Website proxy | `WEBSITE/app/api/security/network-diagnostics/route.ts` | Proxy to MAS for SOC |
| Subagent definition | `.cursor/agents/network-monitor.md` | Cursor @network-monitor invocation |

## API Endpoints (MAS)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/network/health` | GET | Service health |
| `/api/network/dns` | GET | DNS check (multi-resolver anomaly detection) |
| `/api/network/dns` | POST | Custom domains DNS check |
| `/api/network/latency` | GET | Ping latency to VMs (187, 188, 189) |
| `/api/network/connectivity` | GET | HTTP connectivity to MAS, MINDEX, Sandbox |
| `/api/network/diagnostics` | GET | Full report |

## DNS Anomaly Detection

Resolvers used: **Cloudflare (1.1.1.1)**, **Google (8.8.8.8)**, **Quad9 (9.9.9.9)**, and **system resolver**.

- If resolvers return **different IPs** for the same domain → possible DNS hijacking or poisoning
- Default domains: `mycosoft.com`, `sandbox.mycosoft.com`, `api.mycosoft.com`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNIFI_HOST` | UniFi controller IP (default 192.168.0.1) |
| `UNIFI_API_KEY` | UniFi API key (X-API-Key) |
| `UNIFI_SITE` | UniFi site (default: default) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CLOUDFLARE_ZONE_ID` | Cloudflare zone ID |
| `WEBSITE_API_URL` | Website URL for UniFi proxy fallback |

## Agent Task Types

| Task Type | Description |
|-----------|-------------|
| `dns_check` | Multi-resolver DNS consistency |
| `latency_check` | Ping to VMs |
| `connectivity_check` | HTTP to services |
| `full_diagnostics` | Full report |
| `topology` | UniFi devices and clients |

## Quick Test

```bash
# Full diagnostics
curl http://192.168.0.188:8001/api/network/diagnostics

# DNS check only
curl "http://192.168.0.188:8001/api/network/dns?domains=mycosoft.com,sandbox.mycosoft.com"
```

## Related

- SOC Network Monitor page: `/security/network` (UniFi dashboard)
- UniFi API: `WEBSITE/app/api/unifi/route.ts`
- Rule: `.cursor/rules/vm-layout-and-dev-remote-services.mdc` (VM IPs)
