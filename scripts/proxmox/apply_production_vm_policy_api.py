#!/usr/bin/env python3
"""
Apply production VM policy on Proxmox via API (and optionally SSH for host cron):

- Discovers VMIDs by QEMU guest agent IPv4 (192.168.0.187–191) when guests are running.
- Merges with PVE_PRODUCTION_VMIDS from env / .credentials.local (comma-separated).
- Sets onboot=1 for each production guest.
- Starts guests that are stopped.
- Optionally installs daily vzdump + ensure-running cron on the PVE host (SSH as root).

Loads secrets only from environment / .credentials.local — never prints tokens or passwords.

Usage (from MAS repo root, after credentials loaded):
  python scripts/proxmox/apply_production_vm_policy_api.py
  python scripts/proxmox/apply_production_vm_policy_api.py --api-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import base64
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO = Path(__file__).resolve().parent.parent.parent

# Canonical LAN octets for production Linux guests (Sandox, MAS, MINDEX, MYCA workspace)
PRODUCTION_IP_OCTETS: Set[int] = {187, 188, 189, 191}


def load_env() -> None:
    for f in (REPO / ".credentials.local",):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def pve_hosts() -> List[str]:
    raw = (
        os.environ.get("PROXMOX_HOSTS")
        or os.environ.get("PROXMOX_HOST")
        or os.environ.get("SANDBOX_PVE_HOST")
        or os.environ.get("PROXMOX_SANDBOX_PVE_HOST")
        or "192.168.0.202"
    )
    return [h.strip() for h in raw.split(",") if h.strip()]


def api_token() -> Tuple[str, str]:
    tid = os.environ.get("PROXMOX_TOKEN_ID") or os.environ.get("PROXMOX202_TOKEN_ID", "")
    sec = os.environ.get("PROXMOX_TOKEN_SECRET") or os.environ.get("PROXMOX202_TOKEN_SECRET", "")
    if "!" in tid and "=" in tid and not sec:
        # Single combined form PROXMOX202_TOKEN=root@pam!id=secret in some env files
        pass
    if tid and sec:
        return tid, sec
    combined = os.environ.get("PROXMOX202_TOKEN", "")
    if combined and "=" in combined:
        left, _, right = combined.partition("=")
        if left and right:
            return left.strip(), right.strip()
    return "", ""


def pve_root_password() -> str:
    return (
        os.environ.get("PROXMOX202_PASSWORD")
        or os.environ.get("PROXMOX_PASSWORD")
        or os.environ.get("PROXMOX_ROOT_PASSWORD")
        or os.environ.get("VM_PASSWORD")
        or os.environ.get("VM_SSH_PASSWORD")
        or ""
    )


def session_for(host: str, token_id: str, token_secret: str) -> requests.Session:
    s = requests.Session()
    s.verify = False
    b = f"https://{host}:8006/api2/json"
    s.headers["Authorization"] = f"PVEAPIToken={token_id}={token_secret}"
    setattr(s, "_pve_base", b)  # type: ignore[attr-defined]
    return s


def session_ticket_auth(host: str, password: str) -> Optional[requests.Session]:
    """Fallback: password ticket (root@pam) when API tokens not configured."""
    s = requests.Session()
    s.verify = False
    base = f"https://{host}:8006/api2/json"
    try:
        r = s.post(
            f"{base}/access/ticket",
            data={"username": "root@pam", "password": password},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        data = r.json().get("data") or {}
        ticket = data.get("ticket")
        csrf = data.get("CSRFPreventionToken")
        if not ticket:
            return None
        s.cookies.set("PVEAuthCookie", ticket, domain="", path="/")
        if csrf:
            s.headers["CSRFPreventionToken"] = csrf
        setattr(s, "_pve_base", base)
        return s
    except Exception:
        return None


def try_connect() -> Tuple[Optional[requests.Session], Optional[str]]:
    tid, sec = api_token()
    for host in pve_hosts():
        if tid and sec:
            s = session_for(host, tid, sec)
            base = getattr(s, "_pve_base")
            try:
                r = s.get(f"{base}/version", timeout=15)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    print(f"OK Proxmox API (token) {host}:8006 version={data.get('version', '?')}")
                    return s, host
            except Exception as e:
                print(f"WARN token {host}: {e}", file=sys.stderr)
        pw = pve_root_password()
        if pw:
            s = session_ticket_auth(host, pw)
            if s:
                base = getattr(s, "_pve_base")
                try:
                    r = s.get(f"{base}/version", timeout=15)
                    if r.status_code == 200:
                        data = r.json().get("data", {})
                        print(f"OK Proxmox API (root ticket) {host}:8006 version={data.get('version', '?')}")
                        return s, host
                except Exception as e:
                    print(f"WARN ticket {host}: {e}", file=sys.stderr)
    print(
        "ERROR: No working Proxmox auth. Add PROXMOX_TOKEN_ID + PROXMOX_TOKEN_SECRET "
        "or ensure PROXMOX202_PASSWORD / VM_PASSWORD matches root@pam on PROXMOX_HOST.",
        file=sys.stderr,
    )
    return None, None


def cluster_vm_map(session: requests.Session) -> Dict[int, Dict[str, Any]]:
    base = getattr(session, "_pve_base")
    r = session.get(f"{base}/cluster/resources", params={"type": "vm"}, timeout=60)
    r.raise_for_status()
    out: Dict[int, Dict[str, Any]] = {}
    for row in r.json().get("data", []):
        if row.get("type") != "qemu":
            continue
        vmid = row.get("vmid")
        if vmid is None:
            continue
        out[int(vmid)] = row
    return out


def guest_ipv4s(session: requests.Session, node: str, vmid: int) -> List[str]:
    base = getattr(session, "_pve_base")
    try:
        r = session.get(
            f"{base}/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces",
            timeout=15,
        )
        if r.status_code != 200:
            return []
        data = r.json().get("data", {}) or {}
        res = data.get("result") or []
        ips: List[str] = []
        for iface in res:
            for addr in iface.get("ip-addresses", []) or []:
                if addr.get("ip-address-type") == "ipv4":
                    ip = addr.get("ip-address")
                    if ip:
                        ips.append(ip)
        return ips
    except Exception:
        return []


def discover_production_vmids(session: requests.Session, vm_map: Dict[int, Dict[str, Any]]) -> Set[int]:
    found: Set[int] = set()
    for vmid, row in vm_map.items():
        if row.get("template"):
            continue
        node = row.get("node")
        if not node:
            continue
        if row.get("status") != "running":
            continue
        for ip in guest_ipv4s(session, node, vmid):
            parts = ip.split(".")
            if len(parts) == 4 and parts[0] == "192" and parts[1] == "168" and parts[2] == "0":
                try:
                    octet = int(parts[3])
                    if octet in PRODUCTION_IP_OCTETS:
                        found.add(vmid)
                        print(f"  discover: VMID {vmid} -> {ip} ({node})")
                except ValueError:
                    pass
    return found


def merge_name_hints(vm_map: Dict[int, Dict[str, Any]], merged: Set[int]) -> None:
    """Add VMIDs whose names indicate MINDEX / MYCA / critical Linux guests."""
    for vmid, row in vm_map.items():
        if row.get("template"):
            continue
        name = (row.get("name") or "").lower()
        hints = ("mindex", "mycosoft-mindex", "myca-workspace", "myca-vm", "mycosoft-myca")
        if any(h in name for h in hints):
            merged.add(vmid)
            print(f"  name-hint: VMID {vmid} -> {row.get('name')}")


def ssh_qm_list_extra_vmids(pve_host: str) -> Set[int]:
    """Parse `qm list` on hypervisor via SSH — catches guests when QEMU agent IPs differ."""
    extra: Set[int] = set()
    pw = pve_root_password()
    if not pw:
        return extra
    try:
        import paramiko
    except ImportError:
        return extra
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(pve_host, username="root", password=pw, timeout=45)
        stdin, stdout, stderr = ssh.exec_command("qm list", timeout=60)
        out = stdout.read().decode("utf-8", errors="replace")
        ssh.close()
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                vid = int(parts[0])
            except ValueError:
                continue
            rest = line.lower()
            if any(
                x in rest
                for x in ("mindex", "myca", "mas", "sandbox", "mycosoft-mindex", "mycosoft-mas")
            ):
                extra.add(vid)
                print(f"  qm-list-hint: VMID {vid} ({line.strip()})")
    except Exception as e:
        print(f"WARN: qm list via SSH: {e}", file=sys.stderr)
    return extra


def env_vmids() -> Set[int]:
    raw = os.environ.get("PVE_PRODUCTION_VMIDS", "").strip()
    if not raw:
        return set()
    out: Set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            print(f"WARN: skip bad PVE_PRODUCTION_VMIDS token {part!r}", file=sys.stderr)
    return out


def default_sandbox_vmid() -> int:
    return int(os.environ.get("SANDBOX_PVE_VMID", "103"))


def set_onboot(session: requests.Session, node: str, vmid: int) -> bool:
    base = getattr(session, "_pve_base")
    r = session.put(f"{base}/nodes/{node}/qemu/{vmid}/config", data={"onboot": 1}, timeout=60)
    if r.status_code >= 400:
        print(f"  onboot PUT vmid={vmid} HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    return True


def start_vm(session: requests.Session, node: str, vmid: int) -> bool:
    base = getattr(session, "_pve_base")
    r = session.post(f"{base}/nodes/{node}/qemu/{vmid}/status/start", timeout=120)
    if r.status_code >= 400:
        print(f"  start POST vmid={vmid} HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    return True


def backup_storage_id(session: requests.Session) -> Optional[str]:
    """First cluster storage that accepts 'backup' content."""
    base = getattr(session, "_pve_base")
    r = session.get(f"{base}/storage", timeout=30)
    if r.status_code != 200:
        return None
    for s in r.json().get("data", []) or []:
        content = (s.get("content") or "").split(",")
        if "backup" in content and s.get("enabled", 1):
            return s.get("storage")
    return None


def ssh_install_host_jobs(pve_host: str, vmids: List[int], backup_stor: Optional[str]) -> None:
    try:
        import paramiko
    except ImportError:
        print("WARN: paramiko not installed; skip SSH host jobs", file=sys.stderr)
        return
    pw = pve_root_password()
    if not pw:
        print("WARN: no Proxmox root password in env; skip SSH host jobs", file=sys.stderr)
        return
    ids_str = " ".join(str(v) for v in sorted(vmids))
    stor = backup_stor or "local"
    ensure_sh = textwrap.dedent(
        f"""\
        #!/bin/bash
        IDS="{ids_str}"
        for vmid in $IDS; do
          st=$(qm status "$vmid" 2>/dev/null | awk '{{print $2}}')
          if [ "$st" = "stopped" ]; then
            logger -t pve-ensure "Starting stopped VM $vmid"
            qm start "$vmid" || true
          fi
        done
        """
    )
    vz_line = (
        f"0 3 * * * root /usr/sbin/vzdump {ids_str} --mode snapshot --compress zstd "
        f"--storage {stor} --quiet 1 --maxfiles 7 2>&1 | logger -t vzdump-daily"
    )
    b64ensure = base64.b64encode(ensure_sh.encode()).decode("ascii")
    b64vz = base64.b64encode((vz_line.strip() + "\n").encode()).decode("ascii")
    crontab_add = textwrap.dedent(
        f"""\
        mkdir -p /etc/mycosoft
        echo {b64ensure} | base64 -d > /usr/local/sbin/pve-ensure-mycosoft.sh
        chmod +x /usr/local/sbin/pve-ensure-mycosoft.sh
        grep -q pve-ensure-mycosoft /etc/crontab 2>/dev/null || echo "*/5 * * * * root /usr/local/sbin/pve-ensure-mycosoft.sh" >> /etc/crontab
        grep -q vzdump-mycosoft /etc/crontab 2>/dev/null || echo {b64vz} | base64 -d >> /etc/crontab
        echo OK_SSH_JOBS
        """
    )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(pve_host, username="root", password=pw, timeout=45)
        stdin, stdout, stderr = ssh.exec_command(crontab_add, timeout=120)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        ssh.close()
        if out.strip():
            print(out)
        if err.strip():
            print(err, file=sys.stderr)
        print(f"SSH install exit_code={code}")
    except Exception as e:
        print(f"SSH install failed: {e}", file=sys.stderr)


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-only", action="store_true", help="Do not SSH to PVE for cron install")
    ap.add_argument("--skip-ssh", action="store_true", help="Same as --api-only")
    args = ap.parse_args()
    api_only = args.api_only or args.skip_ssh

    session, host = try_connect()
    if not session or not host:
        return 3

    vm_map = cluster_vm_map(session)
    discovered = discover_production_vmids(session, vm_map)
    explicit = env_vmids()
    merged: Set[int] = set(discovered) | set(explicit)
    merged.add(default_sandbox_vmid())
    merge_name_hints(vm_map, merged)
    merged |= ssh_qm_list_extra_vmids(host)

    if os.environ.get("PVE_INCLUDE_VM191", "").strip() in ("1", "true", "yes"):
        merged.add(191)

    print(f"Target production VMIDs: {sorted(merged)}")

    backup_stor = backup_storage_id(session)
    if backup_stor:
        print(f"Backup storage selected: {backup_stor}")
    else:
        print("WARN: No storage with content=backup found; vzdump will use 'local' if SSH runs")

    for vmid in sorted(merged):
        row = vm_map.get(vmid)
        if not row:
            print(f"WARN: VMID {vmid} not in cluster resources — skip", file=sys.stderr)
            continue
        node = row.get("node")
        status = row.get("status")
        name = row.get("name", "")
        if not node:
            continue
        print(f"--- VMID {vmid} ({name}) node={node} status={status}")
        if set_onboot(session, node, vmid):
            print(f"  onboot=1 OK")
        if status == "stopped":
            print(f"  starting stopped VM...")
            if start_vm(session, node, vmid):
                print(f"  start issued OK")

    if not api_only:
        ssh_install_host_jobs(host, sorted(merged), backup_stor)
    else:
        print("Skipping SSH cron install (--api-only)")

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
