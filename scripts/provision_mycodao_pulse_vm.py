#!/usr/bin/env python3
"""
Provision Ubuntu Server 24.04 LTS (Noble) cloud-init image on Proxmox for MycoDAO + Pulse (Next.js in Docker).

Default sizing targets production: enough RAM/CPU for Node SSR, Pulse API routes, SSE, and MAS/MINDEX client calls.

**Proxmox host:** defaults to **192.168.0.90** (node **pve3**). MycoDAO is created only here — not on
**192.168.0.202**, which hosts the production Mycosoft stack (website / MAS / MINDEX / MYCA guests). Do not
point this script at 202 for MycoDAO. After the guest is up, configure MYCODAO to *call* MAS and MINDEX APIs
over the LAN (188 / 189); that does not modify those VMs.

Default guest LAN IP: 192.168.0.198 (avoid 192.168.0.192–195 — C-Suite range in repo docs).

Credentials (never commit secrets — use .credentials.local):
  - SSH: root@PVE_SSH_HOST — PROXMOX_PASSWORD or VM_PASSWORD (same chain as other PVE scripts)
  - API: PROXMOX_TOKEN for /cluster/nextid on 90 when MYCODAO_VM_VMID unset (or ticket auth via password)

Environment:
  MYCODAO_VM_IP        — static guest IP (default 192.168.0.198; avoid 192–195)
  MYCODAO_VM_PREFIX    — CIDR prefix (default 24)
  MYCODAO_VM_GW        — gateway (default 192.168.0.1)
  MYCODAO_VM_DNS       — nameserver (default 192.168.0.1)
  MYCODAO_VM_HOSTNAME  — guest + qm name (default mycodao-pulse)
  MYCODAO_VM_CIUSER    — cloud-init user (default mycosoft)
  MYCODAO_VM_CIPASSWORD — guest password (default: VM_PASSWORD chain)
  MYCODAO_VM_MEMORY    — MB RAM (default 8192 — Next.js + Docker overhead)
  MYCODAO_VM_CORES     — vCPU (default 4 — Pulse + API concurrency)
  MYCODAO_VM_DISK_G    — root disk GiB after import (default 64 — OS, Docker layers, .next, logs)
  MYCODAO_VM_VMID      — fixed VMID; if unset, uses /cluster/nextid via API
  PVE_SSH_HOST         — Proxmox host for SSH (default 192.168.0.90)
  PVE_API_HOST         — API host (default same as PVE_SSH_HOST)
  PVE_API_PORT         — (default 8006)
  PVE_NODE             — Proxmox node name in UI (default pve3)
  PVE_STORAGE          — (default local-lvm)
  PVE_BRIDGE           — (default vmbr0)
  MQTT_VM_SSH_KEYS     — re-used key name: optional path to .pub for cloud-init

Usage:
  python scripts/provision_mycodao_pulse_vm.py
  python scripts/provision_mycodao_pulse_vm.py --dry-run
  python scripts/provision_mycodao_pulse_vm.py --recreate
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.csuite.provision_base import load_credentials, pve_request  # noqa: E402
from infra.csuite.provision_ssh import pve_ssh_exec  # noqa: E402

# Ubuntu Server 24.04 LTS (Noble Numbat) — minimal cloud image, security updates via cloud-init
UBUNTU_CLOUD_IMG = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CACHE_NAME = "noble-server-cloudimg-amd64.img"


def _b64_pipe_openssl_hash(password: str) -> str:
    b64 = base64.b64encode(password.encode("utf-8")).decode("ascii")
    return f"echo {b64} | base64 -d | openssl passwd -6 -stdin"


def _resolve_password(creds: dict[str, str]) -> str:
    return (
        (os.environ.get("MYCODAO_VM_CIPASSWORD") or "").strip()
        or creds.get("vm_password")
        or creds.get("proxmox_password")
        or ""
    )


def _next_vmid(host: str, port: int, creds: dict[str, str]) -> int | None:
    ok, data = pve_request("/cluster/nextid", host=host, port=port, creds=creds)
    if not ok or data is None:
        return None
    try:
        return int(data) if isinstance(data, int) else int(str(data).strip())
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision MycoDAO Pulse VM on Proxmox")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    parser.add_argument("--recreate", action="store_true", help="qm destroy --purge before create")
    args = parser.parse_args()

    creds = load_credentials()
    pve_ssh = os.environ.get("PVE_SSH_HOST", "192.168.0.90").strip()
    pve_api_host = os.environ.get("PVE_API_HOST", pve_ssh).strip()
    pve_port = int(os.environ.get("PVE_API_PORT", "8006"))
    node = os.environ.get("PVE_NODE", "pve3").strip()
    storage = os.environ.get("PVE_STORAGE", "local-lvm").strip()
    bridge = os.environ.get("PVE_BRIDGE", "vmbr0").strip()

    ip = (os.environ.get("MYCODAO_VM_IP") or "192.168.0.198").strip()
    prefix = (os.environ.get("MYCODAO_VM_PREFIX") or "24").strip()
    gw = (os.environ.get("MYCODAO_VM_GW") or "192.168.0.1").strip()
    dns = (os.environ.get("MYCODAO_VM_DNS") or "192.168.0.1").strip()
    hostname = (os.environ.get("MYCODAO_VM_HOSTNAME") or "mycodao-pulse").strip()
    ciuser = (os.environ.get("MYCODAO_VM_CIUSER") or "mycosoft").strip()
    mem_mb = int((os.environ.get("MYCODAO_VM_MEMORY") or "8192").strip())
    cores = int((os.environ.get("MYCODAO_VM_CORES") or "4").strip())
    disk_g = (os.environ.get("MYCODAO_VM_DISK_G") or "64").strip()

    pw = _resolve_password(creds)
    if not pw:
        print(
            "ERROR: Set MYCODAO_VM_CIPASSWORD or VM_PASSWORD / VM_SSH_PASSWORD for cloud-init user.",
            file=sys.stderr,
        )
        return 1

    vmid_env = (os.environ.get("MYCODAO_VM_VMID") or "").strip()
    if vmid_env:
        vmid = int(vmid_env)
    else:
        vmid = _next_vmid(pve_api_host, pve_port, creds)
        if vmid is None:
            print(
                "ERROR: Could not get /cluster/nextid (set PROXMOX_TOKEN and password for API, or set "
                "MYCODAO_VM_VMID explicitly). Target API host must match PVE_API_HOST (default 192.168.0.90).",
                file=sys.stderr,
            )
            return 1

    ssh_keys_path = (os.environ.get("MYCODAO_VM_SSH_KEYS") or os.environ.get("MQTT_VM_SSH_KEYS") or "").strip()
    sshkey_part = ""
    if ssh_keys_path:
        p = Path(ssh_keys_path)
        if p.exists():
            key_body = p.read_text(encoding="utf-8").strip()
            b64k = base64.b64encode(key_body.encode("utf-8")).decode("ascii")
            sshkey_part = (
                f"echo {b64k} | base64 -d > /tmp/mycodao_ci_sshkey && "
                f"qm set {vmid} --sshkeys /tmp/mycodao_ci_sshkey && rm -f /tmp/mycodao_ci_sshkey && "
            )
        else:
            print(f"WARN: MYCODAO_VM_SSH_KEYS file missing: {ssh_keys_path}", file=sys.stderr)

    img_path = f"/var/lib/vz/template/cache/{CACHE_NAME}"

    hash_cmd = _b64_pipe_openssl_hash(pw)
    remote_script = f"""set -euo pipefail
NODE_CHK=$(hostname -s || hostname)
echo "Running on Proxmox host: $NODE_CHK (expected node in UI: {node})"
test -f "{img_path}" || wget -q --show-progress -O "{img_path}" "{UBUNTU_CLOUD_IMG}"
"""

    if args.recreate:
        remote_script += f"""
qm status {vmid} >/dev/null 2>&1 && qm stop {vmid} --skiplock 2>/dev/null || true
sleep 2
qm status {vmid} >/dev/null 2>&1 && qm destroy {vmid} --purge || true
"""

    remote_script += f"""
CIDIR=$(mktemp -d)
trap 'rm -rf "$CIDIR"' EXIT
{hash_cmd} > "$CIDIR/cipw.hash"
HASH=$(cat "$CIDIR/cipw.hash")

qm create {vmid} \\
  --name {hostname} \\
  --memory {mem_mb} \\
  --cores {cores} \\
  --cpu host \\
  --agent 1 \\
  --onboot 1 \\
  --ostype l26 \\
  --scsihw virtio-scsi-single \\
  --net0 virtio,bridge={bridge} \\
  --serial0 socket \\
  --vga serial0 \\
  --boot order=scsi0 \\
  --description "MycoDAO + Pulse | Ubuntu 24.04 LTS cloud | Next.js Docker | see MYCODAO repo"

qm importdisk {vmid} "{img_path}" {storage}
qm set {vmid} --scsi0 {storage}:vm-{vmid}-disk-0,discard=on
qm resize {vmid} scsi0 {disk_g}G
qm set {vmid} --ide2 {storage}:cloudinit
qm set {vmid} --ciuser {ciuser}
qm set {vmid} --cipassword "$HASH"
qm set {vmid} --ipconfig0 ip={ip}/{prefix},gw={gw}
qm set {vmid} --nameserver {dns}
qm set {vmid} --searchdomain local 2>/dev/null || true
{sshkey_part}
qm set {vmid} --citype nocloud
echo "VM {vmid} created. Starting..."
qm start {vmid}
echo "Done. Guest: SSH {ciuser}@{ip} after cloud-init."
"""

    print("=== MycoDAO Pulse VM provision ===")
    print(f"  PVE SSH host:  {pve_ssh}")
    print(f"  Node (UI):     {node}")
    print(f"  VMID:          {vmid}")
    print(f"  Name/hostname: {hostname}")
    print(f"  IP:            {ip}/{prefix} gw {gw}")
    print(f"  RAM / disk:    {mem_mb} MB / {disk_g} GB")
    print(f"  Storage/bridge:{storage} / {bridge}")

    if args.dry_run:
        safe = remote_script
        b64pw = base64.b64encode(pw.encode("utf-8")).decode("ascii")
        safe = safe.replace(b64pw, "<REDACTED_BASE64_PASSWORD>")
        print("\n--- remote script (dry run, secrets redacted) ---\n")
        print(safe)
        return 0

    root_pw = (
        creds.get("proxmox_password")
        or creds.get("proxmox202_password")
        or creds.get("vm_password")
        or ""
    )
    if not root_pw:
        print(
            "ERROR: No Proxmox root SSH password (PROXMOX_PASSWORD or VM_PASSWORD for root@PVE_SSH_HOST).",
            file=sys.stderr,
        )
        return 1

    payload = base64.b64encode(remote_script.encode("utf-8")).decode("ascii")
    ok, out = pve_ssh_exec(
        pve_ssh,
        "root",
        root_pw,
        f"echo {payload} | base64 -d | bash",
        timeout=3600,
    )
    print(out)
    if not ok:
        return 1

    print("\nNext steps:")
    print(f"  1. Wait for cloud-init; ping / ssh {ciuser}@{ip}")
    print("  2. On guest: install Docker; clone MYCODAO; copy .env.production; docker compose up -d")
    print("  3. Point MYCODAO env at MAS http://192.168.0.188:8001 and MINDEX http://192.168.0.189:8000 (client only; no VM changes on 188/189).")
    print("  4. DNS: point pulse.mycodao.com to this IP (or Cloudflare Tunnel). See MYCODAO docs.")
    print("  5. Reserve IP in DHCP / Proxmox snapshot after first good deploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
