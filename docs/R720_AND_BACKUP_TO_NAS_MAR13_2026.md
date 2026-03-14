# R720 PowerEdge Location and Backup-to-NAS Strategy — March 13, 2026

**Date:** March 13, 2026  
**Status:** Reference / Action Required  
**Related:** [NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md](./NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md), [NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md](./NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md)

---

## R720 PowerEdge — Where It Is

| Property | Value |
|----------|-------|
| **IP** | 192.168.0.120 |
| **MAC** | 84:2B:2B:46:13:EE |
| **Role** | PowerEdge R710/R720 — C-Suite VM host |
| **UniFi name** | poweredge-r720-csuite |
| **Reachability** | Ping succeeds (1 ms) |
| **SSH** | **Authentication failed** (root + VM_PASSWORD) |

**Important:** 192.168.0.90 is **not** a Proxmox host. Per the IP/MAC map, 0.90 is a **UniFi AP or switch** (MAC 24:6E:96:60:65:CC). There is no Proxmox at 0.90 unless it was changed later.

**R720 vs Proxmox 202:**
- **Proxmox 202:** 192.168.0.202, MAC 84:2B:2B:46:13:**E6** — VM host for 187–191
- **R720:** 192.168.0.120, MAC 84:2B:2B:46:13:**EE** — Different machine

### Next Steps for R720

1. **Verify SSH credentials** — R720 may use different root password than Proxmox 202. Try:
   - `ssh root@192.168.0.120` with your known root password
   - Or `ssh mycosoft@192.168.0.120` if a non-root user exists
2. **Confirm Proxmox** — Once in, run `pveversion` or `qm list` to confirm Proxmox is installed
3. **Assess capacity** — `df -h`, `free -h`, `lsblk` to see disk/RAM for production VMs
4. **Production host** — If R720 has Proxmox and space, it can run production; clone script can target R720 instead of Proxmox 202

---

## 192.168.0.90 — Clarification

| Property | Value |
|----------|-------|
| **IP** | 192.168.0.90 |
| **MAC** | 24:6E:96:60:65:CC |
| **Role** | UniFi AP or switch (network gear) |
| **Proxmox** | No — not a Proxmox host per docs |

If you meant another host for backups (e.g. R720 at 0.120), use 192.168.0.120.

---

## Proxmox 202 Disk Space Issue

- **Sandbox VM 103:** 2056 GB allocated (thin provisioned); actual usage is less
- **Clone failure:** `vzdump --storage local` writes to `/var/lib/vz/dump` on Proxmox 202 — ran out of space at ~14% (~300 GB)
- **Solution:** Back up to **NAS** (or another Proxmox) instead of local disk

---

## Backup to NAS (27+16 TB)

### Prerequisites

1. **NFS export on NAS (192.168.0.105)**  
   On UniFi Drive: Services → NFS → add rule for 192.168.0.202 and share "share".  
   **Note:** If "This Hostname or IP address already exists", edit the existing 192.168.0.202 rule to add the "share" share.  
   **Status (Mar 13, 2026):** `showmount -e 192.168.0.105` from Proxmox 202 returns **empty** — no exports visible. Fix NFS config on UniFi Drive and ensure the rule includes the share.

   **API automation:** `scripts/_unifi_drive_nfs_api.py` configures NFS via UniFi API. Credentials are read from `.credentials.local` (UNIFI_USERNAME, UNIFI_PASSWORD). No prompts — ensure those keys exist.

2. **Proxmox 202** — root SSH access (verified; root + PROXMOX202_PASSWORD works).

### Step 1: Add NFS Storage on Proxmox 202

SSH to 192.168.0.202 as root, then:

```bash
# Discover NFS exports (replace with your NAS IP if different)
pvesm scan nfs 192.168.0.105

# Add NFS storage for backups (adjust export path to match your NAS share)
pvesm add nfs nas-backup \
  --server 192.168.0.105 \
  --export /volume1/proxmox-backups \
  --content backup \
  --options vers=3,soft
```

**Synology NFS:** Export path is often `/volume1/<share_name>`. Create a shared folder (e.g. `proxmox-backups`) and use its NFS path.

### Step 2: Use NAS Storage for vzdump

```bash
vzdump 103 --mode snapshot --compress zstd --storage nas-backup
```

Or set in `/etc/vzdump.conf`:
```
storage: nas-backup
tmpdir: /var/lib/vz/dump
```

**Performance:** For VMs on local disk, `tmpdir` on local disk (default) is fine — vzdump writes locally first, then moves to NFS. For large VMs, consider `--tmpdir /var/lib/vz/dump` (local) to avoid slow NFS writes during backup.

### Step 3: Clone Script

The clone script supports `BACKUP_STORAGE` env var or `--storage` CLI arg:

```powershell
# Option 1: Env var
$env:BACKUP_STORAGE = "nas-backup"
python scripts/_clone_sandbox_to_production_186.py

# Option 2: CLI arg
python scripts/_clone_sandbox_to_production_186.py --storage nas-backup
```

When using `nas-backup`, backups stay on the NAS (not deleted); when using `local`, the backup is removed after restore to free space.

---

## Backup to Another Proxmox (e.g. R720)

If R720 has Proxmox and NFS or sufficient local storage:

1. Add NFS storage on Proxmox 202 pointing to R720’s NFS export, **or**
2. Run the clone from R720: copy backup from NAS to R720, then `qmrestore` there
3. Or use Proxmox PBS (Proxmox Backup Server) if you deploy it

**Current status:** R720 SSH auth failed — resolve credentials before using it as a backup or production host.

---

## Summary

| Item | Action |
|------|--------|
| **R720** | 192.168.0.120 — fix SSH, confirm Proxmox, assess capacity |
| **0.90** | UniFi AP — not Proxmox |
| **NAS** | 192.168.0.105 — add NFS export, add storage on Proxmox 202, use for vzdump |
| **Clone script** | Use `--storage nas-backup` or `BACKUP_STORAGE=nas-backup` to avoid local disk full |

---

## Related

- [MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md](./MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md) — Production clone flow
- [NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md](./NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md) — Full IP/MAC map
- Script: `scripts/_clone_sandbox_to_production_186.py` — supports `--storage nas-backup` or `BACKUP_STORAGE` env
