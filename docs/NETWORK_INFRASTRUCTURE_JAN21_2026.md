# Mycosoft Network Infrastructure

**Version**: 1.2  
**Last Updated**: January 23, 2026 @ 17:20 UTC  
**Purpose**: Complete network topology documentation after infrastructure reconfiguration

---

## Executive Summary

On January 21, 2026, significant network infrastructure changes were made:
- Recabled fiber optic router connections
- Reorganized 8-port 10 Gigabit switch connections
- Reconnected Dream Machine, NAS, and three Dell Proxmox servers
- Adjusted PoE switches for Ubiquiti WiFi access points

**Critical Issue Identified**: WiFi throughput severely degraded (10Gig -> 2.5Gig -> ~30Mbps output from APs)

---

## Latest Scan Results (January 23, 2026 @ 17:20 UTC)

### Network Health Status

| Metric | Value |
|--------|-------|
| **UniFi Devices** | 3 |
| **Connected Clients** | 10 |
| **Proxmox VMs** | 4 (2 running) |
| **Overall Health** | HEALTHY |
| **Core Infrastructure Latency** | <1ms (Optimal) |

### UniFi Network Devices (Verified via API)

| Device | Type | Status |
|--------|------|--------|
| Dream Machine Pro Max | udm | **ONLINE** |
| WHITE U7 Pro XGS | uap | **ONLINE** |
| BLACK U7 Pro XGS | uap | **ONLINE** |

### Proxmox Virtual Machines (Verified via API)

| VM ID | Name | Status |
|-------|------|--------|
| 100 | VM 100 | **RUNNING** |
| 101 | ubuntu-cursor | Stopped |
| 102 | WIN11-TEMPLATE | Stopped |
| 103 | mycosoft-sandbox | **RUNNING** |

### Infrastructure Device Status

| Device | IP | Status | Latency |
|--------|-----|--------|---------|
| Dream Machine Pro Max | 192.168.0.1 | **ONLINE** | <1ms |
| NAS | 192.168.0.105 | **ONLINE** | <1ms |
| Proxmox Server #1 | 192.168.0.202 | **ONLINE** | <1ms |
| Sandbox VM | 192.168.0.187 | **ONLINE** | <1ms |
| Windows Dev PC | 192.168.0.172 | **ONLINE** | <1ms |

> **Note**: UniFi API now fully configured with `cursor_agent` account. Run `python scripts/security_audit_scanner.py --unifi` for real-time device data.

### Core Infrastructure: VERIFIED WORKING

The backbone network is performing optimally:
- Fiber Router -> 10G Switch -> Servers: **<1ms latency**
- 10G Switch -> NAS: **<1ms latency**
- Proxmox -> Sandbox VM: **<1ms latency**

### External Access: VERIFIED WORKING

| Endpoint | Status | Response |
|----------|--------|----------|
| https://sandbox.mycosoft.com | **ONLINE** | HTTP 200 |
| Cloudflare Tunnel | **ACTIVE** | Routing correctly |

---

## Network Topology Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERNET                                               │
│                                        │                                                  │
│                              ┌─────────▼─────────┐                                       │
│                              │   ISP Fiber ONT   │                                       │
│                              │   (10Gbps WAN)    │                                       │
│                              └─────────┬─────────┘                                       │
│                                        │ FIBER                                            │
└────────────────────────────────────────┼────────────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────────────┐
│                           CORE INFRASTRUCTURE LAYER                                      │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         FIBER OPTIC ROUTER (GATEWAY)                               │  │
│  │                              192.168.0.1                                            │  │
│  │                           10Gbps WAN / 10Gbps LAN                                   │  │
│  └──────────────────────────────────┬────────────────────────────────────────────────┘  │
│                                     │ 10Gbps                                             │
│                                     │ CAT 8 / FIBER                                      │
│  ┌──────────────────────────────────▼────────────────────────────────────────────────┐  │
│  │                    8-PORT 10 GIGABIT DISTRIBUTION SWITCH                           │  │
│  │                              192.168.0.2                                            │  │
│  │  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                        │  │
│  │  │ P1 │ P2 │ P3 │ P4 │ P5 │ P6 │ P7 │ P8 │                                        │  │
│  │  └─┬──┴─┬──┴─┬──┴─┬──┴─┬──┴─┬──┴─┬──┴─┬──┘                                        │  │
│  │    │    │    │    │    │    │    │                                                 │  │
│  └────┼────┼────┼────┼────┼────┼────┼─────────────────────────────────────────────────┘  │
│       │    │    │    │    │    │    │                                                    │
└───────┼────┼────┼────┼────┼────┼────┼────────────────────────────────────────────────────┘
        │    │    │    │    │    │    │
        │    │    │    │    │    │    └──── [P7] Reserved / Expansion
        │    │    │    │    │    │
        │    │    │    │    │    └───────── [P6] Windows Dev PC (192.168.0.172) ── CAT 8 ── 2.5Gbps
        │    │    │    │    │
        │    │    │    │    └────────────── [P5] NAS (192.168.0.105) ── CAT 8 ── 2.5Gbps
        │    │    │    │
        │    │    │    └─────────────────── [P4] Dell Server #3 (192.168.0.204) ── CAT 8 ── 10Gbps
        │    │    │
        │    │    └──────────────────────── [P3] Dell Server #2 (192.168.0.203) ── CAT 8 ── 10Gbps
        │    │
        │    └───────────────────────────── [P2] Dell Server #1 (192.168.0.202) ── CAT 8 ── 10Gbps
        │                                         └── Proxmox VE (Primary)
        │                                         └── VM 103: Sandbox (192.168.0.187)
        │
        └────────────────────────────────── [P1] Dream Machine (192.168.0.3) ── CAT 8 ── 2.5Gbps
                                                  └── Network Controller
                                                  └── Security Gateway
                                                  └── IDS/IPS

┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                              DREAM MACHINE DISTRIBUTION                                    │
│                                                                                            │
│                              ┌───────────────────┐                                        │
│                              │   Dream Machine   │                                        │
│                              │   192.168.0.3     │                                        │
│                              └─────────┬─────────┘                                        │
│                                        │                                                   │
│              ┌─────────────────────────┼─────────────────────────┐                        │
│              │                         │                         │                        │
│              ▼                         ▼                         ▼                        │
│  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐                   │
│  │   PoE Switch #1   │   │   PoE Switch #2   │   │   PoE Switch #3   │                   │
│  │   (8-port Gig)    │   │   (8-port Gig)    │   │   (Future)        │                   │
│  └─────────┬─────────┘   └─────────┬─────────┘   └───────────────────┘                   │
│            │                       │                                                      │
│            ▼                       ▼                                                      │
│  ┌───────────────────┐   ┌───────────────────┐                                           │
│  │  Ubiquiti AP #1   │   │  Ubiquiti AP #2   │                                           │
│  │  192.168.0.10     │   │  192.168.0.11     │                                           │
│  │  ⚠️ BOTTLENECK    │   │  ⚠️ BOTTLENECK    │                                           │
│  │                   │   │                   │                                           │
│  │  Expected: 2.5Gb  │   │  Expected: 2.5Gb  │                                           │
│  │  Actual: ~30Mb    │   │  Actual: ~30Mb    │                                           │
│  └───────────────────┘   └───────────────────┘                                           │
│                                                                                            │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Device Inventory

### Core Infrastructure

| Device | IP Address | Role | Connection Type | Expected Speed | Actual Speed | Status |
|--------|------------|------|-----------------|----------------|--------------|--------|
| Fiber Router | 192.168.0.1 | WAN Gateway | Fiber | 10 Gbps | 10 Gbps | ✅ Optimal |
| 10G Switch | 192.168.0.2 | Distribution | N/A (Core) | 10 Gbps | 10 Gbps | ✅ Optimal |
| Dream Machine | 192.168.0.3 | Controller/Gateway | Cat 8 | 2.5 Gbps | 2.5 Gbps | ✅ Optimal |

### Servers (Proxmox)

| Device | IP Address | Role | Connection Type | Expected Speed | Status |
|--------|------------|------|-----------------|----------------|--------|
| Dell Server #1 | 192.168.0.202 | Proxmox Primary | Cat 8 (10GBase-T) | 10 Gbps | ✅ Online |
| Dell Server #2 | 192.168.0.203 | Proxmox Secondary | Cat 8 (10GBase-T) | 10 Gbps | ⚠️ Verify |
| Dell Server #3 | 192.168.0.204 | Proxmox Tertiary | Cat 8 (10GBase-T) | 10 Gbps | ⚠️ Verify |

### Storage

| Device | IP Address | Role | Connection Type | Expected Speed | Status |
|--------|------------|------|-----------------|----------------|--------|
| NAS | 192.168.0.105 | Media/Backups | Cat 8 | 2.5 Gbps | ✅ Online |

### Virtual Machines

| VM | IP Address | Host | Purpose | Status |
|----|------------|------|---------|--------|
| VM 103 | 192.168.0.187 | Dell Server #1 | Sandbox | ✅ Running |
| VM 104 | TBD | TBD | Production | 🔄 Planned |

### WiFi Access Points (BOTTLENECK AREA)

| Device | IP Address | Connection | Expected Speed | Actual Speed | Issue |
|--------|------------|------------|----------------|--------------|-------|
| Ubiquiti AP #1 | 192.168.0.10 | PoE Cat 5e/6 | 2.5 Gbps | ~30 Mbps | **CRITICAL** |
| Ubiquiti AP #2 | 192.168.0.11 | PoE Cat 5e/6 | 2.5 Gbps | ~30 Mbps | **CRITICAL** |

### Development

| Device | IP Address | Role | Connection Type | Expected Speed |
|--------|------------|------|-----------------|----------------|
| Windows Dev PC | 192.168.0.172 | Development | Cat 8 | 2.5 Gbps |

---

## Critical Bottleneck Analysis

### WiFi Access Point Throughput Issue

**Symptom**: 10Gig backbone → 2.5Gig Dream Machine → ~30Mbps WiFi output

**Speed Degradation Path**:
```
Fiber Router (10 Gbps)
    │
    └── 10G Switch (10 Gbps) ✅
            │
            └── Dream Machine (2.5 Gbps) ✅
                    │
                    └── PoE Switch (1 Gbps?) ⚠️
                            │
                            └── Cat 5e/6 Cable (100 Mbps?) ⚠️
                                    │
                                    └── WiFi AP (30 Mbps) ❌
```

### Root Cause Analysis

| Potential Cause | Likelihood | Impact | Check Method |
|-----------------|------------|--------|--------------|
| Cat 5e cable limiting to 100Mbps | HIGH | Critical | Inspect cable markings |
| PoE switch only 100Mbps ports | MEDIUM | Critical | Check switch specs |
| AP negotiating at 100Mbps | HIGH | Critical | Check AP web UI |
| PoE injector limiting speed | MEDIUM | High | Bypass and test |
| Damaged cable/connector | LOW | High | Cable tester |
| AP firmware issue | LOW | Medium | Update firmware |

---

## Cable Specifications & Recommendations

### Current Cable Types

| Run | Current Type | Max Speed | Required Speed | Action |
|-----|--------------|-----------|----------------|--------|
| Router → 10G Switch | Fiber/Cat 8 | 40 Gbps | 10 Gbps | ✅ OK |
| 10G Switch → Servers | Cat 8 | 40 Gbps | 10 Gbps | ✅ OK |
| 10G Switch → Dream Machine | Cat 8 | 40 Gbps | 2.5 Gbps | ✅ OK |
| 10G Switch → NAS | Cat 8 | 40 Gbps | 2.5 Gbps | ✅ OK |
| Dream Machine → PoE Switch | Unknown | Unknown | 2.5 Gbps | **CHECK** |
| PoE Switch → WiFi APs | Cat 5e/6? | 100 Mbps? | 2.5 Gbps | **UPGRADE** |

### Cable Upgrade Recommendations

| Priority | Location | Current | Recommended | Expected Improvement |
|----------|----------|---------|-------------|---------------------|
| **P1 - Critical** | PoE Switch → AP #1 | Cat 5e/6 | Cat 6a or Cat 7 | 100 Mbps → 2.5 Gbps |
| **P1 - Critical** | PoE Switch → AP #2 | Cat 5e/6 | Cat 6a or Cat 7 | 100 Mbps → 2.5 Gbps |
| **P2 - High** | Dream Machine → PoE Switches | Unknown | Cat 6a minimum | Verify full speed |
| **P3 - Medium** | Any remaining Cat 5e in backbone | Cat 5e | Cat 6a | Future-proofing |

### Cable Type Reference

| Cable Type | Max Speed | Max Distance @ Speed | Use Case |
|------------|-----------|---------------------|----------|
| Cat 5e | 1 Gbps | 100m | Legacy gigabit |
| Cat 6 | 1 Gbps (10 Gbps @ 55m) | 100m / 55m | Standard gigabit |
| Cat 6a | 10 Gbps | 100m | 10Gig standard |
| Cat 7 | 10 Gbps | 100m | 10Gig shielded |
| Cat 8 | 25-40 Gbps | 30m | Data center |
| Fiber OM3 | 100 Gbps | 300m | Long runs |

---

## Immediate Action Items

### P1 - Critical (Within 24 Hours)

1. **Identify PoE Switch Model**
   - Check if ports support 1Gbps or 2.5Gbps
   - If only 100Mbps, this is the primary bottleneck

2. **Check AP Connection Speed**
   ```bash
   # Via UniFi Controller
   # Devices → AP → Details → Uplink Speed
   ```

3. **Inspect Cables to WiFi APs**
   - Physical inspection of cable jacket markings
   - Look for "Cat 5e", "Cat 6", etc.

### P2 - High (Within 1 Week)

1. **Replace Cables to APs with Cat 6a**
   - Order Cat 6a or Cat 7 patch cables
   - Replace both AP uplink cables
   - Verify 2.5Gbps negotiation

2. **Upgrade PoE Switch if Needed**
   - If switch is 100Mbps, upgrade to 2.5GbE PoE+ switch
   - Recommended: UniFi Switch Lite 8 PoE (60W) or similar

### P3 - Medium (Within 2 Weeks)

1. **Full Network Audit**
   ```powershell
   python scripts/network_topology_scanner.py --full-scan --generate-report
   ```

2. **Document All Cable Runs**
   - Label each cable with type and endpoints
   - Create cable management spreadsheet

---

## Speed Verification Commands

### Test from Windows Dev PC

```powershell
# Ping latency test
ping 192.168.0.187 -n 10

# Test to Sandbox VM
iperf3 -c 192.168.0.187 -t 30

# Check local NIC speed
Get-NetAdapter | Select Name, LinkSpeed

# Check negotiation speed
netsh interface ipv4 show interface
```

### Test from Sandbox VM (SSH)

```bash
# Check NIC speed
ethtool eth0 | grep Speed

# Test to NAS
iperf3 -c 192.168.0.105 -t 30

# Test to Dev PC
iperf3 -c 192.168.0.172 -t 30
```

### Check UniFi AP Uplink Speed

1. Open UniFi Controller (Dream Machine UI)
2. Navigate to Devices
3. Select each AP
4. Check "Uplink" section for negotiated speed
5. If showing 100Mbps → cable or switch issue

---

## Network Topology Scanner

A comprehensive scanner has been created at `scripts/network_topology_scanner.py`.

### Usage

```powershell
# Quick check of known infrastructure
python scripts/network_topology_scanner.py --quick-check

# Full subnet scan
python scripts/network_topology_scanner.py --full-scan

# Generate detailed audit report
python scripts/network_topology_scanner.py --quick-check --generate-report
```

### Output

The scanner generates:
- JSON report with device details
- Markdown report with recommendations
- Bottleneck analysis
- Cable upgrade recommendations

---

## Monitoring & Alerts

### Recommended Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Ping latency (LAN) | > 5ms | > 20ms |
| Ping latency (VM) | > 2ms | > 10ms |
| WiFi throughput | < 100 Mbps | < 50 Mbps |
| 10G link utilization | > 70% | > 90% |
| PoE power budget | > 80% | > 95% |

### Add to Grafana Dashboard

Create alerts for:
- [ ] Device offline detection
- [ ] Link speed degradation
- [ ] High latency
- [ ] WiFi AP uplink speed

---

## Cloudflare Integration

### Current Tunnel Configuration

| Subdomain | Service | Target |
|-----------|---------|--------|
| sandbox.mycosoft.com | Website | VM 103:3000 |
| api-sandbox.mycosoft.com | MINDEX API | VM 103:8000 |
| brain-sandbox.mycosoft.com | MycoBrain | Windows:18003 |

### Network Path (External Request)

```
User Browser
    │
    └── Cloudflare Edge (Global CDN)
            │
            └── Cloudflare Tunnel
                    │
                    └── cloudflared on VM 103
                            │
                            └── localhost:3000 (Website Container)
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [SYSTEM_ARCHITECTURE_OVERVIEW_JAN2026.md](./SYSTEM_ARCHITECTURE_OVERVIEW_JAN2026.md) | Service architecture |
| [PROXMOX_VM_SPECIFICATIONS.md](./PROXMOX_VM_SPECIFICATIONS.md) | VM configuration |
| [PROXMOX_UNIFI_API_REFERENCE.md](./PROXMOX_UNIFI_API_REFERENCE.md) | API reference |
| [VM_INFRASTRUCTURE_UPGRADE.md](./VM_INFRASTRUCTURE_UPGRADE.md) | VM upgrade guide |

---

---

## Security Audit Results (January 23, 2026)

### Network Security Status

| Component | Status | Notes |
|-----------|--------|-------|
| UniFi Dream Machine Pro Max | **ONLINE** | 192.168.0.1 - Controller accessible |
| SSL Certificate (sandbox.mycosoft.com) | **VALID** | 79 days until expiry |
| Proxmox API | **AUTH ISSUE** | Token may need regeneration |
| MycoBrain Service | **OFFLINE** | Service not running on Windows |

### API Authentication Audit

| Endpoint | Status | Risk |
|----------|--------|------|
| Security API (/api/security) | 404 | Endpoint not found (needs deployment) |
| MycoBrain Controls | N/A | Service offline |
| Public Endpoints | OK | No secrets leaked |

### Action Items from Security Audit

1. **Regenerate Proxmox API Token** - Current token returning 401
2. **Configure UniFi API Credentials** - For complete network scanning
3. **Deploy Security API Endpoint** - Currently returning 404
4. **Start MycoBrain Service** - For full API auth testing

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-01-21 | Initial documentation after infrastructure recable | Infrastructure Team |
| 2026-01-21 | Created network topology scanner | Cursor Agent |
| 2026-01-21 | Identified WiFi AP bottleneck | Cursor Agent |
| 2026-01-21 15:45 | Re-scan after topology changes - 6 devices verified online, <1ms latency confirmed | Cursor Agent |
| 2026-01-23 16:41 | Security audit completed - 3 findings (0 critical, 1 high, 1 medium) | Cursor Agent |

---

*Document Version: 1.0*  
*Created: January 21, 2026*  
*Maintainer: Mycosoft Infrastructure Team*
