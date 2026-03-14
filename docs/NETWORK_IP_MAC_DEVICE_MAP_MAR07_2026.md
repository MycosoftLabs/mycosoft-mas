# Network IP/MAC/Device Map — March 7, 2026

**Date:** March 7, 2026  
**Status:** Complete (ARP scan validated)  
**Source:** `scripts/network_arp_scan.py` — ARP-based scan of 192.168.0.0/24

---

## Overview

This document provides a full IP → MAC → role map of the Mycosoft network. Use it to:

1. **Know all resources** — PCs, servers, Proxmox, NodeFather, C-Suite hosts
2. **Plan C-Suite migration** — Move CEO/CFO/CTO/COO VMs to R720 (192.168.0.120)
3. **Keep site on Proxmox** — Website, MAS, MINDEX, MYCA workstation remain on Proxmox 202
4. **Run heavy agents on R720** — Voice, Earth2, inference workloads on the big machine

---

## DHCP / IP Allocation (User-Specified)

| Range | Purpose |
|-------|---------|
| .5–.8 | Domain Controller |
| .10 | File server / NAS |
| .11–.15 | *Open* (reserved) |
| .16–.21 | Database server, Chrome |
| .200–.243 | DHCP pool (dynamic) |

**Static reservations:** Do not change. Full plan: [NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md](./NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md).

---

## Scan Summary

| Metric | Value |
|--------|-------|
| Subnet | 192.168.0.0/24 |
| Devices found | 27 (excluding broadcast .255) |
| Method | ARP cache after ping sweep |
| Raw data | `data/network_arp_scan_20260307.json` |

---

## Full Device Map (IP → MAC → Role)

| IP | MAC | Role | Host |
|----|-----|------|------|
| **192.168.0.1** | 58:D6:1F:21:13:18 | UniFi UDM / Gateway | Router |
| **192.168.0.2** | 24:6E:96:63:7F:14 | UniFi AP or switch | Network |
| **192.168.0.7** | F8:B1:56:D2:39:62 | NodeFather Ubuntu | Crypto |
| **192.168.0.11** | BC:24:11:49:C8:E7 | PC/Workstation | TBD |
| **192.168.0.17** | 58:41:46:E3:29:0D | PC/Device | TBD |
| **192.168.0.34** | 84:7B:EB:F5:E3:C2 | **Edge R630 #2** | Dell server |
| **192.168.0.49** | A8:9C:6C:2A:AD:7A | PC/Device | TBD |
| **192.168.0.66** | F8:B1:56:AD:CC:AF | NodeFather Ubuntu | Crypto |
| **192.168.0.67** | B8:CA:3A:85:52:57 | NodeFather Ubuntu | Crypto |
| **192.168.0.68** | 8C:30:66:7A:3F:70 | PC/Device | TBD |
| **192.168.0.69** | 18:66:DA:1C:37:FF | PC/Device | TBD |
| **192.168.0.85** | 84:7B:EB:F7:61:F6 | **Edge R630 #1** | Dell server |
| **192.168.0.90** | 24:6E:96:60:65:CC | UniFi AP or switch | Network |
| **192.168.0.93** | 90:B1:1C:8E:34:84 | PC/Device | TBD |
| **192.168.0.100** | E8:39:35:5D:34:B6 | PC/Device | TBD |
| **192.168.0.105** | 6C:63:F8:37:12:26 | **NAS** | Synology / storage |
| **192.168.0.112** | F8:B1:56:BD:08:48 | NodeFather Ubuntu | Crypto |
| **192.168.0.120** | 84:2B:2B:46:13:EE | **PowerEdge R710/R720** | C-Suite host |
| **192.168.0.136** | A0:02:A5:C7:B7:BC | PC/Device | TBD |
| **192.168.0.183** | 84:78:48:CA:31:4C | PC/Device | TBD |
| **192.168.0.186** | *(clone of 187)* | **Production VM** | Proxmox 202 (mycosoft.com) |
| **192.168.0.187** | BC:24:11:9D:9F:55 | **Sandbox VM** | Proxmox 202 |
| **192.168.0.188** | BC:24:11:60:DB:33 | **MAS VM** | Proxmox 202 |
| **192.168.0.189** | BC:24:11:B1:0D:05 | **MINDEX VM** | Proxmox 202 |
| **192.168.0.190** | *(not in scan)* | **GPU node VM** | Proxmox 202 (likely off) |
| **192.168.0.191** | BC:24:11:CF:B1:0F | **MYCA workstation VM** | Proxmox 202 |
| **192.168.0.192–195** | *(not in scan)* | C-Suite VMs (CEO/CFO/CTO/COO) | To migrate to R720 |
| **192.168.0.201** | 34:17:EB:B7:D5:E8 | NodeFather Ubuntu | Crypto |
| **192.168.0.202** | 84:2B:2B:46:13:E6 | **Proxmox host** | VM host (187–191) |
| **192.168.0.239** | B8:CA:3A:A7:44:58 | NodeFather Ubuntu | Crypto |

---

## Architecture: Where Things Live

### Proxmox 202 (192.168.0.202) — Public-facing, KEEP

| VM | IP | Purpose |
|----|-----|---------|
| Production | 186 | Website (mycosoft.com), no MycoBrain |
| Sandbox | 187 | Website (sandbox.mycosoft.com), MycoBrain host |
| MAS | 188 | Multi-Agent System, orchestrator |
| MINDEX | 189 | Database + vector store |
| GPU node | 190 | Voice, Earth2, inference |
| MYCA workspace | 191 | MYCA AI Secretary, n8n |

**Action:** No change. Site stays here with MAS, MINDEX, MYCA.

### R720 (192.168.0.120) — Internal C-Suite + Heavy Agents

| Resource | IP | Purpose |
|----------|-----|---------|
| R720 host | 120 | Proxmox or bare metal for C-Suite |
| csuite-ceo | 192 | CEO workstation (Claude, Cursor, OpenClaw) |
| csuite-cfo | 193 | CFO workstation |
| csuite-cto | 194 | CTO workstation |
| csuite-coo | 195 | COO workstation |
| *(future)* | 196+ | Heavy agents (voice, Earth2, GPU workloads) |

**Action:** Migrate C-Suite VMs from Proxmox 202 → R720. Run heavy agents on R720.

### NodeFather (Crypto) — 6 Ubuntu machines

| IP | MAC | Status |
|----|-----|--------|
| 7 | F8:B1:56:D2:39:62 | Live |
| 66 | F8:B1:56:AD:CC:AF | Live |
| 67 | B8:CA:3A:85:52:57 | Live |
| 112 | F8:B1:56:BD:08:48 | Live |
| 201 | 34:17:EB:B7:D5:E8 | Live |
| 239 | B8:CA:3A:A7:44:58 | Live |

### Other Servers

| IP | Device | Role |
|----|--------|------|
| 85 | Edge R630 #1 | Dell server (TBD) |
| 34 | Edge R630 #2 | Dell server (TBD) |
| 105 | NAS | Storage (\\192.168.0.105\mycosoft.com) |

---

## Migration Plan: C-Suite to R720

1. **R720 (192.168.0.120)** has Proxmox or equivalent; C-Suite VMs will run here.
2. **Proxmox 202** keeps only 187–191 (Sandbox, MAS, MINDEX, GPU, MYCA).
3. **C-Suite VMs 192–195** move from Proxmox 202 → R720.
4. **Heavy agents** (PersonaPlex, Earth2, GPU inference) run on R720 when not on GPU node 190.

### Config changes

- `config/proxmox202_csuite.yaml` → `config/r720_csuite.yaml` with host `192.168.0.120`
- Update docs: VM_LAYOUT, SYSTEM_REGISTRY, this topology

---

## Devices Not in Scan (Off or Different Segment)

| IP | Expected Role |
|----|---------------|
| 190 | GPU node VM — may be powered off |
| 192–195 | C-Suite VMs — on Proxmox 202 until migration |

---

## UniFi Labeling (Apply in Controller)

| IP | MAC | UniFi Name |
|----|-----|------------|
| 7 | F8:B1:56:D2:39:62 | nodefather-ubuntu-7 |
| 34 | 84:7B:EB:F5:E3:C2 | edge-r630-2 |
| 66 | F8:B1:56:AD:CC:AF | nodefather-ubuntu-66 |
| 67 | B8:CA:3A:85:52:57 | nodefather-ubuntu-67 |
| 85 | 84:7B:EB:F7:61:F6 | edge-r630-1 |
| 105 | 6C:63:F8:37:12:26 | nas |
| 112 | F8:B1:56:BD:08:48 | nodefather-ubuntu-112 |
| 120 | 84:2B:2B:46:13:EE | poweredge-r720-csuite |
| 186 | *(clone of 187)* | vm-production |
| 187 | BC:24:11:9D:9F:55 | vm-sandbox |
| 188 | BC:24:11:60:DB:33 | vm-mas |
| 189 | BC:24:11:B1:0D:05 | vm-mindex |
| 191 | BC:24:11:CF:B1:0F | vm-myca |
| 201 | 34:17:EB:B7:D5:E8 | nodefather-ubuntu-201 |
| 202 | 84:2B:2B:46:13:E6 | proxmox-202-public |
| 239 | B8:CA:3A:A7:44:58 | nodefather-ubuntu-239 |

---

## Related Documents

- [NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md](./NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md) — Topology and C-Suite migration
- [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md) — VM layout
- Script: `scripts/network_arp_scan.py`
- Raw scan: `data/network_arp_scan_20260307.json`
