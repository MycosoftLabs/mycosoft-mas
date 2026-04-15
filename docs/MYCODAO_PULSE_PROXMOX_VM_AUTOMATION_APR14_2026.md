# MycoDAO Pulse — Proxmox VM automation — April 14, 2026

## Where the VM is created

| Host | Role for MycoDAO |
|------|------------------|
| **192.168.0.90** | **Only** Proxmox used to create and run the **new MycoDAO Pulse** guest. Defaults: `PVE_SSH_HOST`, `PVE_API_HOST`, node **`pve3`** — same pattern as `scripts/provision_mqtt_broker_vm_pve90.py`. |
| **192.168.0.202** | **Not** used for MycoDAO provisioning. That environment hosts the production Mycosoft stack (website, MAS, MINDEX, MYCA, etc.). **Do not** run `provision_mycodao_pulse_vm.py` against 202 for MycoDAO; do not repurpose those guests for Pulse. |

## After the guest is up: MAS and MINDEX

MycoDAO runs on its **own** VM (guest IP, e.g. **192.168.0.198** by default). It **connects to** existing services as HTTP clients only:

- **MAS:** `http://192.168.0.188:8001`
- **MINDEX:** `http://192.168.0.189:8000`

Set these in MYCODAO `.env` / `.env.production` (and any server-side proxy URLs). No requirement to change MAS or MINDEX VMs for “MycoDAO” beyond normal API keys / CORS / firewall rules if you lock down the LAN.

## Security

- **Do not** commit Proxmox passwords or API tokens. Use `.credentials.local` or process env: `PROXMOX_PASSWORD`, `VM_PASSWORD`, `PROXMOX_TOKEN`, `MYCODAO_VM_CIPASSWORD`.
- For API auth to **90**, use `PROXMOX_TOKEN` (or ticket auth via password). `PROXMOX202_*` applies to **202**’s API in other scripts.

## Guest OS and sizing (MycoDAO site + Pulse)

- **OS:** **Ubuntu Server 24.04 LTS** (Noble) — official minimal cloud image from `cloud-images.ubuntu.com`, cloud-init for network and user. Suitable for Docker + Node/Next.js.
- **Defaults (new provisions):** **4 vCPU**, **8 GB RAM**, **64 GB** disk — tuned for Next.js production, Pulse routes/SSE, Docker overhead, and outbound calls to MAS/MINDEX. Override with `MYCODAO_VM_CORES`, `MYCODAO_VM_MEMORY`, `MYCODAO_VM_DISK_G` if the host is constrained.
- **Already created with smaller specs?** In Proxmox: **Hardware** → increase memory/CPU; **Disk** → resize through the UI or run `qm resize` on the host, **or** destroy and re-run the script with `--recreate` (new defaults apply on create).

## Defaults (script)

| Setting | Default |
|--------|---------|
| Proxmox SSH / API | `192.168.0.90` |
| Node (UI) | `pve3` |
| Guest static IP | `192.168.0.198` (avoid **192.168.0.192–195** — C-Suite range in repo docs) |
| Guest OS | Ubuntu **24.04 LTS** (cloud image) |
| Hardware | **4** vCPU, **8** GB RAM, **64** GB disk |

## Commands

From MAS repo root (after loading credentials):

```powershell
.\scripts\provision-mycodao-pulse-vm.ps1 -DryRun
.\scripts\provision-mycodao-pulse-vm.ps1
.\scripts\provision-mycodao-pulse-vm.ps1 -Recreate
```

Or: `python scripts/provision_mycodao_pulse_vm.py [--dry-run] [--recreate]`

## Related

- `scripts/provision_mqtt_broker_vm_pve90.py` — same Proxmox **90** / **pve3** defaults.
- `infra/csuite/provision_base.py` — `load_credentials`, `pve_request`.
- `infra/csuite/provision_ssh.py` — `pve_ssh_exec`.
