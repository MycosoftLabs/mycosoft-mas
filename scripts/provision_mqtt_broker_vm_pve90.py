#!/usr/bin/env python3
"""
Provision Ubuntu Server 24.04 LTS (cloud-init) on Proxmox for Mosquitto (MycoBrain + Jetson).

Target: https://192.168.0.90:8006 — node pve3 (override with PVE_NODE / PVE_SSH_HOST).

Hardware default: 2 vCPU, 2 GB RAM, 20 GB disk (virtio-scsi + cloud image resize).

Requires:
  - SSH root@PVE_SSH_HOST (password: PROXMOX_PASSWORD / VM_PASSWORD / VM_SSH_PASSWORD via .credentials.local)
  - Optional API: PROXMOX_TOKEN for /cluster/nextid (else VMID from MQTT_VM_VMID)

Environment (important):
  MQTT_VM_IP       — static guest IP, e.g. 192.168.0.196 (required)
  MQTT_VM_PREFIX   — CIDR prefix, default 24
  MQTT_VM_GW       — default gateway, default 192.168.0.1
  MQTT_VM_DNS      — nameserver for cloud-init, default 192.168.0.1
  MQTT_VM_HOSTNAME — guest + Proxmox name, default mycobrain-mqtt
  MQTT_VM_CIUSER   — cloud-init user, default mycosoft
  MQTT_VM_CIPASSWORD — guest sudo user password (default: VM_PASSWORD chain)
  MQTT_VM_SSH_KEYS  — path to a public key file to inject (optional)
  PVE_SSH_HOST     — SSH target (Proxmox node that runs qm), default 192.168.0.90
  PVE_NODE         — Proxmox node name (for API nextid only), default pve3
  PVE_STORAGE      — disk storage id, default local-lvm
  PVE_BRIDGE       — vmbr, default vmbr0
  MQTT_VM_VMID     — fixed VMID; if unset, uses /cluster/nextid when API auth works

Usage:
  python scripts/provision_mqtt_broker_vm_pve90.py
  python scripts/provision_mqtt_broker_vm_pve90.py --dry-run
  python scripts/provision_mqtt_broker_vm_pve90.py --recreate   # destroy same VMID first
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

UBUNTU_CLOUD_IMG = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CACHE_NAME = "noble-server-cloudimg-amd64.img"


def _b64_pipe_openssl_hash(password: str) -> str:
    """Return command fragment: hash via openssl on remote, password via base64 pipe."""
    b64 = base64.b64encode(password.encode("utf-8")).decode("ascii")
    return f"echo {b64} | base64 -d | openssl passwd -6 -stdin"


def _resolve_password(creds: dict[str, str]) -> str:
    return (
        (os.environ.get("MQTT_VM_CIPASSWORD") or "").strip()
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
    parser = argparse.ArgumentParser(description="Provision MQTT broker VM on Proxmox pve3")
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

    ip = (os.environ.get("MQTT_VM_IP") or "").strip()
    if not ip:
        print("ERROR: Set MQTT_VM_IP (static guest IP), e.g. MQTT_VM_IP=192.168.0.196", file=sys.stderr)
        return 1

    prefix = (os.environ.get("MQTT_VM_PREFIX") or "24").strip()
    gw = (os.environ.get("MQTT_VM_GW") or "192.168.0.1").strip()
    dns = (os.environ.get("MQTT_VM_DNS") or "192.168.0.1").strip()
    hostname = (os.environ.get("MQTT_VM_HOSTNAME") or "mycobrain-mqtt").strip()
    ciuser = (os.environ.get("MQTT_VM_CIUSER") or "mycosoft").strip()

    pw = _resolve_password(creds)
    if not pw:
        print("ERROR: Set MQTT_VM_CIPASSWORD or VM_PASSWORD / VM_SSH_PASSWORD for cloud-init user.", file=sys.stderr)
        return 1

    vmid_env = (os.environ.get("MQTT_VM_VMID") or "").strip()
    if vmid_env:
        vmid = int(vmid_env)
    else:
        vmid = _next_vmid(pve_api_host, pve_port, creds)
        if vmid is None:
            print(
                "ERROR: Could not get /cluster/nextid (API auth?). Set MQTT_VM_VMID explicitly.",
                file=sys.stderr,
            )
            return 1

    ssh_keys_path = (os.environ.get("MQTT_VM_SSH_KEYS") or "").strip()
    sshkey_part = ""
    if ssh_keys_path:
        p = Path(ssh_keys_path)
        if p.exists():
            key_body = p.read_text(encoding="utf-8").strip()
            # qm set --sshkeys expects a file on the server; use echo base64 workaround
            b64k = base64.b64encode(key_body.encode("utf-8")).decode("ascii")
            sshkey_part = f"echo {b64k} | base64 -d > /tmp/mqtt_ci_sshkey && qm set {vmid} --sshkeys /tmp/mqtt_ci_sshkey && rm -f /tmp/mqtt_ci_sshkey && "
        else:
            print(f"WARN: MQTT_VM_SSH_KEYS file missing: {ssh_keys_path}", file=sys.stderr)

    img_path = f"/var/lib/vz/template/cache/{CACHE_NAME}"

    # Build remote script (bash -e)
    hash_cmd = _b64_pipe_openssl_hash(pw)
    remote_script = f"""set -euo pipefail
NODE_CHK=$(hostname -s || hostname)
echo "Running on Proxmox host: $NODE_CHK (expected node name in UI: {node})"
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
  --memory 2048 \\
  --cores 2 \\
  --cpu host \\
  --agent 1 \\
  --onboot 1 \\
  --ostype l26 \\
  --scsihw virtio-scsi-single \\
  --net0 virtio,bridge={bridge} \\
  --serial0 socket \\
  --vga serial0 \\
  --boot order=scsi0 \\
  --description "Mosquitto MQTT (MycoBrain+Jetson); Ubuntu 24.04 cloud-init; single-purpose broker VM"

qm importdisk {vmid} "{img_path}" {storage}
qm set {vmid} --scsi0 {storage}:vm-{vmid}-disk-0,discard=on
qm resize {vmid} scsi0 20G
qm set {vmid} --ide2 {storage}:cloudinit
qm set {vmid} --ciuser {ciuser}
qm set {vmid} --cipassword "$HASH"
qm set {vmid} --ipconfig0 ip={ip}/{prefix},gw={gw}
qm set {vmid} --nameserver {dns}
# --hostname not supported on some PVE builds; guest name comes from qm create --name via cloud-init meta
qm set {vmid} --searchdomain local 2>/dev/null || true
{sshkey_part}
qm set {vmid} --citype nocloud
echo "VM {vmid} created. Starting..."
qm start {vmid}
echo "Done. Guest should DHCP/static via cloud-init: SSH {ciuser}@{ip} when cloud-init finishes."
"""

    print("=== MQTT broker VM provision ===")
    print(f"  PVE SSH host:  {pve_ssh}")
    print(f"  Node (UI):     {node}")
    print(f"  VMID:          {vmid}")
    print(f"  Name/hostname: {hostname}")
    print(f"  IP:            {ip}/{prefix} gw {gw}")
    print(f"  Storage/bridge:{storage} / {bridge}")
    print(f"  Image:         Ubuntu 24.04 LTS cloud ({UBUNTU_CLOUD_IMG})")

    if args.dry_run:
        safe = remote_script
        # Never print credential material in dry-run
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
        print("ERROR: No Proxmox root SSH password (PROXMOX_PASSWORD / VM_PASSWORD).", file=sys.stderr)
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
    print("  2. On the guest: copy scripts/bootstrap_mqtt_broker_guest.sh and run sudo ./bootstrap_mqtt_broker_guest.sh")
    print("  3. Reserve this IP in DHCP; snapshot VM in Proxmox after Mosquitto works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
