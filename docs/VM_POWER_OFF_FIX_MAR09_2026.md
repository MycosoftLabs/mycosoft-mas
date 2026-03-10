# VM Power-Off Fix — Sandbox, C-Suite, Always-On Policy

**Date**: March 9, 2026  
**Status**: Action Required  
**Purpose**: Fix VMs powering off; ensure Sandbox, MAS, MINDEX, and C-Suite stay on 24/7.

---

## Overview

Sandbox VM (187) and C-Suite VMs (192–195, MYCA 191) have been shutting down. This must never happen for production services. This document provides the investigation checklist and fix steps.

---

## Critical VMs — Must Stay On 24/7

| VM | IP | Role | Proxmox Host | VMID |
|----|-----|------|--------------|------|
| **Sandbox** | 192.168.0.187 | Website (Docker), MycoBrain | TBD | TBD |
| **MAS** | 192.168.0.188 | Orchestrator, n8n, Ollama | TBD | TBD |
| **MINDEX** | 192.168.0.189 | PostgreSQL, Redis, Qdrant, API | TBD | TBD |
| **CEO** | 192.168.0.192 | C-Suite CEO workstation | Proxmox 202 (192.168.0.202) | 192 |
| **CFO** | 192.168.0.193 | C-Suite CFO workstation | Proxmox 202 | 193 |
| **CTO** | 192.168.0.194 | C-Suite CTO (Forge) workstation | Proxmox 202 | 194 |
| **COO** | 192.168.0.195 | C-Suite COO workstation | Proxmox 202 | 195 |
| **MYCA** | 192.168.0.191 | MYCA AI Secretary, n8n | Proxmox 202 | 191 |

**Note**: Sandbox, MAS, and MINDEX VMIDs and Proxmox host are not documented. You must identify them in your Proxmox UI or via `qm list` on each node.

---

## Root Cause Investigation Checklist

When a VM powers off, check these in order:

### 1. Proxmox `onboot` Setting

VMs **must** have `onboot 1` so they auto-start after a host reboot or power loss.

```bash
# On each Proxmox node, for each VM:
qm set <VMID> -onboot 1

# Verify
qm config <VMID> | grep onboot
```

If `onboot` is `0` or missing, the VM will **not** start when the host boots.

### 2. Host Reboot or Power Loss

- Did the **Proxmox host** reboot? (power outage, Windows update, maintenance)
- If the host rebooted and `onboot 0`, VMs stay off until manually started.

### 3. Resource Exhaustion (OOM, CPU, Disk)

- **Proxmox 202** runs 5 C-Suite VMs (192, 193, 194, 195, 191). Each C-Suite VM: ~16 GB RAM, 4 cores.
- If the host runs out of RAM or CPU, Proxmox may kill VMs or they may fail to start.
- **Action**: Check host memory and CPU in Proxmox Summary. If near limit, consider moving C-Suite to a separate host.

### 4. Backup or Maintenance Jobs

- Proxmox backup jobs can **stop** VMs during backup if configured that way.
- Check: Datacenter → Backup → verify jobs do not stop critical VMs, or schedule during low-use windows.

### 5. Manual Shutdown

- Confirm no one manually stopped VMs (including via Proxmox UI or `qm stop`).

### 6. Host Power Management

- Ensure the **physical host** does not sleep, hibernate, or power off (BIOS, OS power settings).

---

## Fix Steps (Execute in Order)

### Step 1: Identify Proxmox Nodes for 187, 188, 189

Sandbox (187), MAS (188), and MINDEX (189) run on one or more Proxmox nodes. Find which:

```bash
# SSH to each Proxmox node you have, then:
qm list
# Look for VMs with IPs 187, 188, 189 (or check VM names)
```

Document the mapping: VMID → IP → Proxmox node.

### Step 2: Enable `onboot 1` for All Critical VMs

**On the node hosting Sandbox (187), MAS (188), MINDEX (189):**

```bash
qm set <VMID_187> -onboot 1
qm set <VMID_188> -onboot 1
qm set <VMID_189> -onboot 1
```

**On Proxmox 202 (192.168.0.202):**

```bash
qm set 192 -onboot 1   # CEO
qm set 193 -onboot 1   # CFO
qm set 194 -onboot 1   # CTO
qm set 195 -onboot 1   # COO
qm set 191 -onboot 1   # MYCA
```

### Step 3: Set Startup Order (Optional but Recommended)

To avoid resource spikes, stagger VM startup:

```bash
# Example: Start MAS first (188), then MINDEX (189), then Sandbox (187)
qm set <VMID_188> -startup order=1
qm set <VMID_189> -startup order=2
qm set <VMID_187> -startup order=3

# C-Suite: Start MYCA first, then CEO, then others
qm set 191 -startup order=1
qm set 192 -startup order=2
qm set 193 -startup order=3
qm set 194 -startup order=4
qm set 195 -startup order=5
```

### Step 4: Verify in Proxmox Web UI

- VM → Options → **Start at boot**: Yes
- VM → Options → **Start/Shutdown order**: Set if used

### Step 5: Document VM-to-Host Mapping

Update this doc or `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` with:

- Which Proxmox node hosts 187, 188, 189
- VMIDs for 187, 188, 189

---

## Resource Split Recommendation

**Problem**: Proxmox 202 may be overloaded with 5 C-Suite VMs + MYCA. If Sandbox, MAS, MINDEX share the same physical host, resource contention can cause instability.

**Recommendation**:

1. **Keep on primary host**: Sandbox (187), MAS (188), MINDEX (189), future production — these are core Mycosoft services.
2. **Move to a separate Proxmox host**: C-Suite VMs (192–195) and MYCA (191) — move to a second server with sufficient RAM/CPU.
3. **Benefit**: Core services get dedicated resources; C-Suite VMs can run on a separate box without affecting website, MAS, or MINDEX.

**Next steps for split**:

- Identify a second Proxmox host (or provision one).
- Migrate VMs 191–195 to the new host.
- Update `config/proxmox202_csuite.yaml` or create a new config for the new host.
- Re-run `onboot 1` on the new host.

---

## Verification

After applying fixes:

1. **Reboot the Proxmox host** (during a maintenance window).
2. Confirm all critical VMs start automatically.
3. Verify services: Sandbox http://192.168.0.187:3000, MAS http://192.168.0.188:8001/health, MINDEX http://192.168.0.189:8000.

---

## Related Documents

- [VM Layout and Dev Remote Services](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
- [CTO VM 194 Authoritative Spec](./CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md)
- [Proxmox 202 C-Suite Config](../config/proxmox202_csuite.yaml)
- [Proxmox 202 Auth Setup](./PROXMOX202_AUTH_SETUP_MAR08_2026.md)
