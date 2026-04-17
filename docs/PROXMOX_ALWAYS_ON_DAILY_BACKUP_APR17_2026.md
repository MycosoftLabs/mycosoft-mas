# Proxmox: always-on production VMs and daily backups — Apr 17, 2026

**Status:** Runbook (apply on your Proxmox host)  
**Why this exists:** A production guest (e.g. MAS at `192.168.0.188`) can be **off** while the LAN is fine. Common causes: Proxmox node rebooted and the guest had **Start at boot = off**; someone **stopped** the guest; the **node** was off, out of power, or OOM; a **manual** `qm stop` or failed migration. This is not acceptable for Sandbox, MAS, MINDEX, or MYCA workspace. The fix is **policy on the hypervisor** (onboot, optional watchdog, scheduled backups), not only “remember to start the VM.”

## 1. Get the real VMIDs (not the IP)

On the Proxmox **node** (SSH as `root`):

```bash
qm list
```

Note the **VMID** column for: Website/Sandbox, MAS, MINDEX, MYCA (and any other “must never be off” guest). The last octet of the IP (187, 188, 189, 191) is **not** the VMID.

## 2. Start at boot (required)

**Option A — script from this repo (on the PVE host):**

```bash
chmod +x pve-set-onboot-production.sh
./pve-set-onboot-production.sh <vmid1> <vmid2> <vmid3> <vmid4>
```

**Option B — per guest in UI:**  
VM → **Options** → **Start at boot** = **Yes**

**Option C — CLI one-liner per guest:**

```bash
qm set <vmid> --onboot 1
```

Result: when the **Proxmox host** boots, these guests are **started automatically** (unless you stop them after boot).

## 3. Optional: boot order and delay (stability)

If one guest must be up before another (e.g. database before app), set **Start/Shutdown order** in the UI, or:

```bash
qm set <vmid> --startup order=1
qm set <vmid2> --startup order=2
qm set <vmid2> --startup up=60
```

(Adjust `order` and `up` seconds to your stack.)

## 4. “Never stay off” — ensure script (optional but recommended)

`pve-ensure-critical-running.sh` runs on the **PVE node** and **starts** any listed guest that is in **stopped** state (e.g. after a mistaken stop, or a stop that should not have been left down).

1. Create config directory: `mkdir -p /etc/mycosoft`
2. Copy `scripts/proxmox/critical-vmids.list.example` to `/etc/mycosoft/pve-critical-vmids` and fill in real **VMIDs** (one per line).
3. Install script: `cp pve-ensure-critical-running.sh /usr/local/sbin/ && chmod +x /usr/local/sbin/pve-ensure-critical-running.sh`
4. Root crontab:

```cron
*/5 * * * * /usr/local/sbin/pve-ensure-critical-running.sh >> /var/log/pve-ensure-critical.log 2>&1
```

**Caveat:** This will **restart** a guest you **intentionally** stopped within 5 minutes. For maintenance, **temporarily** remove that VMID from the list or comment the cron.

**Caveat 2:** If the guest is **not** `stopped` but is **hung** (on, but no network), this script does not fix that; use **QEMU guest agent**, service health checks, or in-guest watchdogs.

## 5. Daily backups (snapshots or backups to storage)

**Preferred: Proxmox UI**

- **Datacenter** → **Backup** → **Add**  
- **Schedule:** daily (choose a low-traffic window)  
- **Selection mode:** include the production VMIDs (or a **Pool** you use for production)  
- **Mode:** `Snapshot` (for online friendly dump) or per your storage policy  
- **Storage:** a storage that accepts **Backups** (e.g. local, NFS, PBS)  
- **Retention:** at least 7 daily, or match your RPO policy  

**Alternative: `vzdump` cron**  
See `scripts/proxmox/pve-vzdump-daily.cron.example` — set real VMIDs and storage name.

**PBS (Proxmox Backup Server):** If you have PBS, point the job at PBS for deduplication and better restore; the same “daily + retention” idea applies.

## 6. Proxmox HA (only in a real cluster)

**HA** in Proxmox (fencing, quorum) is for **multi-node** clusters. A **single** PVE node does not get “HA” in the Proxmox sense. For one node, **onboot + ensure script + UPS + host health** is the right stack. If you have **3+ cluster nodes** and shared storage, add the production resources to `ha-manager` per `docs/infrastructure/PROXMOX_HA_CLUSTER.md` and test fence/restore.

## 7. What we do not get for “free”

- **Power loss** on the **node** with no UPS: everything is off until power returns. **UPS + apcupsd** (or similar) is part of “never off” in the real world.  
- **Disk / full ZFS pool / host OOM:** the guest may not start; fix the **node** and **storage** first.  
- **Intentional** `qm stop` for work: the **ensure** script will start it again; use a maintenance window and remove the ID from the list as above.

## 8. Autonomous agent path (preferred)

Agents run from the dev PC or any machine on the LAN with `.credentials.local` loaded:

```powershell
cd <MAS-repo>
# Load .credentials.local into process env (same pattern as deploy scripts)
Get-Content .credentials.local | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process') } }
python scripts/proxmox/apply_production_vm_policy_api.py
```

**Requires in `.credentials.local`:** `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET` (Datacenter → Permissions → API Tokens on PVE). Optional: `PROXMOX_HOST` or `PROXMOX_HOSTS` (default `192.168.0.202`), `PVE_PRODUCTION_VMIDS` (comma-separated VMIDs if discovery is incomplete), `PROXMOX202_PASSWORD` or `VM_PASSWORD` for root SSH when installing `/etc/crontab` jobs.

The script sets **onboot**, **starts** stopped production guests, discovers VMIDs by guest IP when the QEMU agent is up, and appends **ensure** + **vzdump** crontab lines on the hypervisor when SSH succeeds.

## 9. Files in the MAS repo

| File | Purpose |
|------|--------|
| `scripts/proxmox/apply_production_vm_policy_api.py` | **Primary**: API + optional SSH install (agents run this) |
| `scripts/proxmox/pve-set-onboot-production.sh` | On-host: set `onboot=1` for listed VMIDs |
| `scripts/proxmox/pve-ensure-critical-running.sh` | On-host cron: start if `stopped` |
| `scripts/proxmox/pve-vzdump-daily.cron.example` | Example `vzdump` line |
| `scripts/proxmox/critical-vmids.list.example` | Template for `/etc/mycosoft/pve-critical-vmids` |

## 10. After you apply

- Reboot the **PVE node** once in a maintenance window and confirm all four (or your set) guests return.  
- Confirm **Datacenter → Backup** job shows **OK** in **Task log** the next day.

## Related

- `docs/PROXMOX_PASSWORD_RESET_GUIDE.md` — `qm list`, `qm start`  
- `docs/infrastructure/PROXMOX_HA_CLUSTER.md` — multi-node HA  
- `docs/PROXMOX_UNIFI_API_REFERENCE.md` — API start/stop (automation from MAS with token)  
