# Mycosoft UniFi Network Infrastructure

**Date:** June 25, 2026  
**Status:** Current (canonical consolidation)  
**Related:** `docs/UBIQUITI_CISA_KEV_REMEDIATION_JUN25_2026.md`, `docs/NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md`, `docs/NETWORK_STATUS_JAN28_2026.md`

---

## Executive summary

| Layer | Canonical |
|-------|-----------|
| **Gateway / controller** | **UniFi Dream Machine Pro Max** @ `192.168.0.1:443` |
| **Core switch** | **USW Pro Max 24 PoE** @ `192.168.0.2` |
| **Production NAS** | **UNAS-Pro / UniFi Drive** @ `192.168.0.105` |
| **Hypervisor** | **Proxmox** @ `192.168.0.202` |
| **MAS monitoring** | `GET /api/network/kev`, `/api/network/diagnostics` on `192.168.0.188:8001` |
| **CISA KEV (Jun 2026)** | UniFi OS chain **PATCHED** (probe); Lantronix **not in inventory** |

**Operator pending:** Confirm UniFi OS version ≥ 5.0.8 in UniFi UI; create **UNIFI_API_KEY** (SSO blocks password login); physical Lantronix closet audit.

**Verified Jun 25, 2026:** MAS `1db70795` on 188; KEV/diagnostics HTTP 200; NAS `.105` SMB/NFS ports open; Lantronix NOT_IN_INVENTORY.

---

## Physical topology

```
Internet
   │
   ▼
UDM Pro Max (192.168.0.1) — gateway, DNS, firewall, UniFi controller, IDS/IPS
   │
   ├── USW Pro Max 24 PoE (192.168.0.2)
   │      ├── Proxmox (192.168.0.202) → VMs 187, 188, 189, 191, …
   │      ├── UNAS-Pro NAS (192.168.0.105)
   │      ├── Legions 241 (voice), 249 (Earth-2)
   │      └── U7 Pro XGS APs (WHITE / BLACK — WiFi bottleneck documented ~30 Mbps)
   └── PoE switches / lab devices (MycoBrain, Jetson gateways)
```

---

## IP / MAC reference (verified + documented)

| IP | Role | MAC (Mar 7 scan) |
|----|------|------------------|
| `.1` | UDM Pro Max | `58:D6:1F:21:13:18` |
| `.2` | USW Pro Max 24 PoE | `24:6E:96:63:7F:14` |
| `.105` | UNAS-Pro NAS | `6C:63:F8:37:12:26` |
| `.120` | PowerEdge R720 (C-Suite target) | — |
| `.172` | Windows dev PC | — |
| `.187` | Sandbox (website Docker, MycoBrain host) | — |
| `.188` | MAS orchestrator | — |
| `.189` | MINDEX (Postgres, Redis, Qdrant, API) | — |
| `.191` | MYCA workspace | — |
| `.196` | MQTT broker | — |
| `.202` | Proxmox primary | `84:2B:2B:46:13:E6` |
| `.241` | Voice Legion (PersonaPlex, Moshi) | — |
| `.249` | Earth-2 Legion | — |

**Superseded:** Jan 2026 docs placing DDM at `.3` or Proxmox at `.90` — use `.1` and `.202` respectively.

---

## NAS mount matrix

### Production NAS — `192.168.0.105` (authoritative for media + MINDEX library)

| Consumer | Path |
|----------|------|
| Windows dev | `\\192.168.0.105\mycosoft.com` |
| Website assets | `\\192.168.0.105\mycosoft.com\website\assets` |
| Sandbox VM 187 | `/opt/mycosoft/media/website/assets` → container `public/assets` |
| MINDEX VM 189 | `/mnt/nas/mindex` (CIFS `//192.168.0.105/mycosoft.com/mindex`) |

**Credentials:** `NAS_SMB_USER`, `NAS_SMB_PASSWORD`, `NAS_CIFS_URL` in `.credentials.local` / VM `.env` only.

### Legacy UDM internal storage — `192.168.0.1` (26 TB)

Documented in `docs/setup/UBIQUITI_NETWORK_INTEGRATION.md` and `docs/infrastructure/UDM_STORAGE_SETUP.md` as `\\192.168.0.1\mycosoft`. **Production website and MINDEX use `.105`**, not UDM internal SMB.

---

## VLANs (planned — not verified live)

| VLAN | Subnet | Purpose |
|------|--------|---------|
| 1 (default) | 192.168.0.0/24 | Current flat LAN (VMs live here today) |
| 20 | 192.168.20.0/24 | Production VMs (planned) |
| 30 | 192.168.30.0/24 | Agent VMs (planned) |
| 40 | 192.168.40.0/24 | IoT / MycoBrain (planned) |

See `docs/infrastructure/VLAN_SECURITY.md` for full target design.

---

## UniFi API integration

### Environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `UNIFI_HOST` | `192.168.0.1` | MAS, website |
| `UNIFI_API_KEY` | — | MAS `unifi_client.py`, website `/api/unifi` |
| `UNIFI_SITE` | `default` | MAS + website |
| `UNIFI_KEV_CHECK_PORT` | `443` | KEV probe |

### MAS endpoints (`192.168.0.188:8001`)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/network/health` | UniFi + DNS health |
| `GET /api/network/diagnostics` | Full network diagnostic bundle |
| `GET /api/network/kev` | CISA KEV status (UniFi + Lantronix inventory) |

### Website

| Route | Purpose |
|-------|---------|
| `GET /api/unifi?action=dashboard` | Admin SOC network dashboard (`/security/network`) |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/security/probe_unifi_kev.py` | Bishop Fox KEV wrapper |
| `scripts/security/cve_2026_34908_check.py` | Vendored detector |
| `scripts/unifi_scan_topology.py` | Legacy username/password scan (failed Mar 7 — prefer API key) |

---

## Security — CISA KEV (June 2026)

| CVE | Product | Mycosoft status |
|-----|---------|-----------------|
| CVE-2026-34908/09/10 | UniFi OS | **PATCHED** @ `192.168.0.1:443` (probe Jun 25) |
| CVE-2025-67038 | Lantronix EDS5000 | **NOT_IN_INVENTORY** (physical audit recommended) |

Full remediation: `docs/UBIQUITI_CISA_KEV_REMEDIATION_JUN25_2026.md`

**References:** [Ubiquiti SAB-064](https://community.ui.com/releases/Security-Advisory-Bulletin-064), [Bishop Fox detector](https://github.com/BishopFox/CVE-2026-34908-check), [CISA Lantronix ICSA-26-069-02](https://www.cisa.gov/news-events/ics-advisories/icsa-26-069-02)

---

## Verification commands

```powershell
# KEV probe (local)
python scripts/security/probe_unifi_kev.py 192.168.0.1 443

# MAS production
curl http://192.168.0.188:8001/api/network/kev
curl http://192.168.0.188:8001/api/network/diagnostics

# NAS reachability
Test-NetConnection 192.168.0.105 -Port 445
```

---

## Documentation gaps (track here)

- UniFi OS **exact version string** from UI (KEV probe confirms **PATCHED** / 5.0.8+ behavior; `/api/system` has no version field)
- **`UNIFI_API_KEY`** — not in any repo; SSO (`isSsoEnabled`) blocks password login (HTTP 499/403); create key in UniFi UI
- AP/switch **firmware versions**
- **WiFi SSID** names and guest policy (not in repo)
- **NFS export list** on `.105` — TCP 2049 open; `showmount` needs `nfs-common` on Linux probe host
- **Physical Lantronix** hardware audit (code + port 30718 scan: none found)

---

## Source doc index (newest first)

| Date | Doc |
|------|-----|
| Jun 25, 2026 | `docs/UBIQUITI_CISA_KEV_REMEDIATION_JUN25_2026.md` |
| Jun 15, 2026 | `docs/AWS_W1_NAS_BACKUP_COMPLETE_JUN15_2026.md` |
| May 27, 2026 | `MINDEX/mindex/docs/MINDEX_LIBRARY_NAS_MOUNT_MAY27_2026.md` |
| May 3, 2026 | `docs/NETWORK_AUTO_DISCOVERY_MAY03_2026.md` |
| Mar 13, 2026 | `docs/R720_AND_BACKUP_TO_NAS_MAR13_2026.md` |
| Mar 7, 2026 | `docs/NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md`, `NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md` |
| Jan 28, 2026 | `docs/NETWORK_STATUS_JAN28_2026.md`, `NETWORK_RECOVERY_COMPLETE_JAN28_2026.md` |
| Jan 2026 | `docs/setup/UBIQUITI_NETWORK_INTEGRATION.md`, `docs/infrastructure/INFRASTRUCTURE_INDEX.md` |
| Feb 12, 2026 | `docs/NETWORK_MONITOR_AGENT_FEB12_2026.md` |
