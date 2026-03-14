# Network Topology and Ubiquiti Labeling Plan — March 7, 2026

**Date**: March 7, 2026  
**Author**: MYCA  
**Status**: Draft — Pending UniFi Scan Validation

**Validation (Mar 7, 2026):** ARP scan (`scripts/network_arp_scan.py`) succeeded; MACs below are from `data/network_arp_scan_20260307.json`. UniFi controller login failed—see [UNIFI_SCAN_RESULTS_MAR07_2026.md](./UNIFI_SCAN_RESULTS_MAR07_2026.md). Full map: [NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md](./NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md).

- **Current validated state:** Public-facing VMs 187–189 (Sandbox, MAS, MINDEX) and 190–191 (GPU, MYCA) are confirmed in use; Proxmox 202 hosts these. C-Suite VMs 192–195 are documented as on Proxmox 202 until migration.
- **Desired target state:** C-Suite VMs 192–195 migrate to R710 (192.168.0.120); Proxmox 202 remains public-facing only (187–191).

## Overview

This document defines:
1. Network topology for 192.168.0.x (UniFi Dream Machine)
2. Segregation of **public-facing services** (Proxmox 202) vs **internal C-Suite automation** (PowerEdge R710)
3. Ubiquiti device labeling for all known hosts
4. C-Suite VM migration from Proxmox 202 to R710
5. NodeFather (crypto) and C-Suite physical machine designations

---

## 1. DHCP / IP Allocation (User-Specified)

**DHCP static reservations:** Do not change; keep as-is.

| Range | Purpose | Notes |
|-------|---------|-------|
| .5–.8 | Domain Controller | Reserved for DC(s) |
| .10 | File server / NAS | Static |
| .11–.15 | *Leave open* | Reserved, unassigned |
| .16–.21 | Database server, Chrome | Reserved for DB + Chrome |
| .200–.243 | DHCP pool | Dynamic leases only |

---

## 2. Device Designations (User-Specified)

### 2.1 NodeFather (Crypto) — 6 Ubuntu Machines

| IP | Role |
|----|------|
| 192.168.0.7 | NodeFather crypto |
| 192.168.0.66 | NodeFather crypto |
| 192.168.0.67 | NodeFather crypto |
| 192.168.0.112 | NodeFather crypto |
| 192.168.0.201 | NodeFather crypto |
| 192.168.0.239 | NodeFather crypto |

### 2.2 C-Suite — 5 Windows 10 Physical Machines

Five dedicated Windows 10 workstations for C-suite operations (distinct from NodeFather). IPs to be confirmed via UniFi scan; label as `csuite-WIN-{role}` once identified.

### 2.3 Servers (Known MAC + IP)

| Device | IP | MAC | Role |
|--------|-----|-----|------|
| **PowerEdge R710/R720** | 192.168.0.120 | 84:2B:2B:46:13:EE | C-Suite VM host (internal automation) |
| **Edge R630 #1** | 192.168.0.85 | 84:7B:EB:F7:61:F6 | Server (role TBD) |
| **Edge R630 #2** | 192.168.0.34 | 84:7B:EB:F5:E3:C2 | Server (role TBD) |
| **Proxmox host** | 192.168.0.202 | 84:2B:2B:46:13:E6 | Sandbox, MAS, MINDEX, MYCA, GPU (public-facing) |

---

## 3. Segregation Architecture

### 3.1 Public-Facing (Proxmox 202 — 192.168.0.202)

| VM | IP | Purpose |
|----|-----|---------|
| Sandbox | 192.168.0.187 | Website (Docker), MycoBrain host |
| MAS | 192.168.0.188 | Multi-Agent System, orchestrator |
| MINDEX | 192.168.0.189 | Database + vector store |
| GPU node | 192.168.0.190 | Voice, Earth2, inference |
| MYCA workspace | 192.168.0.191 | MYCA AI Secretary, n8n |

**Keep unchanged.** No C-Suite VMs on this host after migration.

### 3.2 Internal C-Suite (R710 — 192.168.0.120)

| VM | IP | Role | Tools |
|----|-----|------|-------|
| csuite-ceo | 192.168.0.192 | CEO | OpenClaw, Perplexity, Claude, Cursor |
| csuite-cfo | 192.168.0.193 | CFO | OpenClaw, Perplexity, Claude, Cursor |
| csuite-cto | 192.168.0.194 | CTO | OpenClaw, Perplexity, Claude, Cursor |
| csuite-coo | 192.168.0.195 | COO | OpenClaw, Perplexity, Claude, Cursor |
| (future) | 192.168.0.196+ | Additional C-Suite | Same stack |

**Migration:** Move C-Suite VMs from Proxmox 202 to R710. Update `config/proxmox202_csuite.yaml` → `config/r710_csuite.yaml` with new Proxmox host `192.168.0.120`.

### 3.3 Segregation Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROXMOX 202 (192.168.0.202)                          │
│                    PUBLIC-FACING — Website, MAS, MINDEX                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  187 Sandbox   │  188 MAS   │  189 MINDEX   │  190 GPU   │  191 MYCA        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ LAN 192.168.0.x
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                        R710 (192.168.0.120)                                 │
│                    INTERNAL — C-Suite VMs only                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  192 CEO   │  193 CFO   │  194 CTO   │  195 COO   │  (future)               │
│  Perplexity, Claude, Cursor, OpenClaw on each                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Proxmox 202:** Internet-facing services; no C-Suite automation.
- **R710:** Internal company automation; C-Suite VMs with OpenClaw, Perplexity, Claude, Cursor.

---

## 4. Ubiquiti Device Labeling Table

Apply these names in UniFi Controller (Clients → Edit → Name) after scan. Use MAC to match when IP may change.

| IP | MAC (partial) | Suggested UniFi Name | Role |
|----|---------------|----------------------|------|
| 192.168.0.7 | F8:B1:56:D2:39:62 | nodefather-ubuntu-7 | NodeFather crypto |
| 192.168.0.34 | 84:7B:EB:F5:E3:C2 | edge-r630-2 | Edge R630 #2 |
| 192.168.0.66 | F8:B1:56:AD:CC:AF | nodefather-ubuntu-66 | NodeFather crypto |
| 192.168.0.67 | B8:CA:3A:85:52:57 | nodefather-ubuntu-67 | NodeFather crypto |
| 192.168.0.85 | 84:7B:EB:F7:61:F6 | edge-r630-1 | Edge R630 #1 |
| 192.168.0.112 | F8:B1:56:BD:08:48 | nodefather-ubuntu-112 | NodeFather crypto |
| 192.168.0.120 | 84:2B:2B:46:13:EE | poweredge-r720-csuite | PowerEdge R720 |
| 192.168.0.187 | BC:24:11:9D:9F:55 | vm-sandbox | Sandbox VM |
| 192.168.0.188 | BC:24:11:60:DB:33 | vm-mas | MAS VM |
| 192.168.0.189 | BC:24:11:B1:0D:05 | vm-mindex | MINDEX VM |
| 192.168.0.190 | (off/not in scan) | vm-gpu | GPU node VM |
| 192.168.0.191 | BC:24:11:CF:B1:0F | vm-myca | MYCA workspace VM |
| 192.168.0.192 | (migrate to R720) | vm-csuite-ceo | C-Suite CEO (on R720) |
| 192.168.0.193 | (migrate to R720) | vm-csuite-cfo | C-Suite CFO (on R720) |
| 192.168.0.194 | (migrate to R720) | vm-csuite-cto | C-Suite CTO (on R720) |
| 192.168.0.195 | (migrate to R720) | vm-csuite-coo | C-Suite COO (on R720) |
| 192.168.0.201 | 34:17:EB:B7:D5:E8 | nodefather-ubuntu-201 | NodeFather crypto |
| 192.168.0.202 | 84:2B:2B:46:13:E6 | proxmox-202-public | Proxmox host |
| 192.168.0.239 | B8:CA:3A:A7:44:58 | nodefather-ubuntu-239 | NodeFather crypto |

**C-Suite Windows 10 physical machines:** Label as `csuite-WIN-1` through `csuite-WIN-5` once identified by UniFi scan.

---

## 5. UniFi Scan Script and Credentials

### 5.1 Run the Scan

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/unifi_scan_topology.py
python scripts/unifi_scan_topology.py --output json  # for machine-readable output
```

### 5.2 Required Credentials

Add to `.credentials.local` (MAS repo):

```
UNIFI_USERNAME=<your-ubiquiti-username>
UNIFI_PASSWORD=<your-ubiquiti-password>
UNIFI_UDM_IP=192.168.0.1
```

If UDM is at a different IP, set `UNIFI_UDM_IP` accordingly.

### 5.3 After Scan

1. Compare scan output to this document.
2. Update the labeling table with actual MACs and IPs.
3. Apply names in UniFi Controller.
4. Restart systems if needed so DHCP/hostnames refresh.

---

## 6. C-Suite Migration Plan (Proxmox 202 → R710)

### 6.1 Prerequisites

- R710 (192.168.0.120) has Proxmox installed and joinable.
- C-Suite VMs (192–195) exist on Proxmox 202.

### 6.2 Steps

1. **Backup C-Suite VMs** on Proxmox 202 (snapshot or vzdump).
2. **Create R710 config:** `config/r710_csuite.yaml` with `proxmox.host: "192.168.0.120"`.
3. **Migrate or clone** VMs 192–195 to R710 (qm migrate, or export/import).
4. **Update static IPs** in VM configs to remain 192.168.0.192–195.
5. **Remove C-Suite VMs** from Proxmox 202 (after verification).
6. **Update docs:** VM layout, SYSTEM_REGISTRY, this topology doc.

### 6.3 Config Change

Current: `config/proxmox202_csuite.yaml` — host 192.168.0.202  
Target: `config/r710_csuite.yaml` — host 192.168.0.120

---

## 6. Interaction and IP Change Documentation

When any IP or topology changes:

1. Update this document.
2. Update `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`.
3. Update `docs/SYSTEM_REGISTRY_FEB04_2026.md`.
4. Update website `.env.local` / VM env if MAS/MINDEX URLs change (they should not for 187–191).
5. Update UniFi device names.

---

## 7. Related Documents

- [VM Layout and Dev Remote Services](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [Proxmox 202 C-Suite Config](../config/proxmox202_csuite.yaml)
- Script: `scripts/unifi_scan_topology.py`
