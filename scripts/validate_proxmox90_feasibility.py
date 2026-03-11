#!/usr/bin/env python3
"""
Validate Proxmox 90 feasibility and guest OS decision gate.

Checks:
  1. Connectivity to Proxmox API at 192.168.0.90:8006
  2. Node, storage, bridge, and build-source prerequisites
  3. macOS vs Windows decision (macOS on non-Apple Proxmox violates Apple EULA)

Usage:
  python scripts/validate_proxmox90_feasibility.py
  python scripts/validate_proxmox90_feasibility.py --update-config

Output: Writes guest_os decision to config/proxmox202_csuite.yaml
"""
import argparse
import json
import os
import socket
import ssl
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "proxmox202_csuite.yaml"


def load_config():
    """Load proxmox202_csuite config."""
    import yaml
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_credentials():
    """Load Proxmox credentials from .credentials.local or env."""
    creds_path = REPO_ROOT / ".credentials.local"
    if creds_path.exists():
        for line in creds_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return {
        "proxmox_token": os.getenv("PROXMOX_TOKEN", ""),
        "proxmox_password": os.getenv("PROXMOX_PASSWORD", "") or os.getenv("VM_PASSWORD", ""),
    }


def check_port(host: str, port: int, timeout: int = 5) -> bool:
    """Check if host:port is reachable."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def pve_request(path: str, method: str = "GET", data: dict = None, creds: dict = None, host: str = "192.168.0.202", port: int = 8006) -> tuple:
    """
    Make Proxmox API request. Returns (success: bool, data: any).
    Uses provision_base compatible credential keys.
    """
    creds = creds or load_credentials()
    api_base = f"https://{host}:{port}/api2/json"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    auth_header = None
    if creds.get("proxmox_token"):
        tok = creds["proxmox_token"].strip()
        if not tok.startswith("PVEAPIToken"):
            tok = f"PVEAPIToken={tok}"
        auth_header = tok
    elif creds.get("proxmox_password"):
        try:
            payload = urllib.parse.urlencode({
                "username": "root@pam",
                "password": creds["proxmox_password"],
            }).encode()
            req = urllib.request.Request(
                f"{api_base}/access/ticket",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            r = urllib.request.urlopen(req, context=ctx, timeout=10)
            ticket = json.loads(r.read())["data"]
            auth_header = f"PVEAuthCookie={ticket['ticket']}"
        except Exception as e:
            return False, str(e)

    if not auth_header:
        return False, "No Proxmox credentials (PROXMOX_TOKEN or PROXMOX_PASSWORD)"

    headers = {"Authorization": auth_header} if auth_header.startswith("PVEAPIToken") else {"Cookie": auth_header}
    if data and method == "POST":
        payload = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    try:
        req = urllib.request.Request(
            api_base + path,
            data=urllib.parse.urlencode(data).encode() if data and method == "POST" else None,
            headers=headers,
            method=method,
        )
        r = urllib.request.urlopen(req, context=ctx, timeout=15)
        out = json.loads(r.read())
        return True, out.get("data", out)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)


def feasibility_gate_macos() -> tuple:
    """
    macOS feasibility gate.
    - Proxmox on x86 non-Apple hardware: Apple EULA prohibits macOS virtualization.
    - Proxmox on Apple Silicon: Not supported by Proxmox VE.
    Decision: macOS is NOT feasible on standard Proxmox. Use Windows.
    """
    return False, "macOS on Proxmox requires Apple hardware; standard Proxmox (x86) cannot legally run macOS guests. Fallback: Windows."


def main():
    parser = argparse.ArgumentParser(description="Validate Proxmox feasibility and set guest OS")
    parser.add_argument("--update-config", action="store_true", help="Write guest_os to config")
    args = parser.parse_args()

    cfg = load_config()
    pve_cfg = cfg.get("proxmox", {})
    PROXMOX_HOST = pve_cfg.get("host", "192.168.0.202")
    PROXMOX_PORT = int(pve_cfg.get("port", 8006))
    PROXMOX_API = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json"

    print("=" * 60)
    print("  Proxmox Feasibility Validation (C-Suite)")
    print(f"  Target: {PROXMOX_HOST}:{PROXMOX_PORT}")
    print("=" * 60)

    # 1. Port connectivity
    print("\n[1/6] Checking Proxmox API port...")
    if check_port(PROXMOX_HOST, PROXMOX_PORT):
        print(f"  OK — {PROXMOX_HOST}:{PROXMOX_PORT} reachable")
    else:
        print(f"  FAIL — {PROXMOX_HOST}:{PROXMOX_PORT} unreachable")
        print("  Ensure Proxmox 90 is on the LAN and firewall allows 8006")
        sys.exit(1)

    # 2. API auth and nodes
    print("\n[2/6] Checking Proxmox API and nodes...")
    creds = load_credentials()
    api_ok, data = pve_request("/nodes", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT)
    if not api_ok:
        print(f"  WARN — API auth skipped: {data}")
        print("  Port is reachable. Set PROXMOX_TOKEN or PROXMOX_PASSWORD for full validation.")
    else:
        nodes = [n["node"] for n in data] if isinstance(data, list) else []
        print(f"  OK — Nodes: {', '.join(nodes)}")

    cfg = load_config()
    pve = cfg.get("proxmox", {})
    node = pve.get("node", "pve")
    storage_name = pve.get("storage", "local-lvm")
    bridge_name = pve.get("bridge", "vmbr0")
    build_source = cfg.get("build_source", {})

    # 3. Storage
    print("\n[3/6] Checking storage prerequisites...")
    ok, data = pve_request(f"/nodes/{node}/storage", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT) if api_ok else (False, "auth skipped")
    if not ok:
        print(f"  WARN — Storage check skipped: {data}")
    else:
        storages = [s["storage"] for s in data] if isinstance(data, list) else []
        if storage_name in storages:
            print(f"  OK — Storage '{storage_name}' exists on node {node}")
        else:
            print(f"  FAIL — Storage '{storage_name}' not found. Available: {', '.join(storages)}")
            sys.exit(1)

    # 4. Bridge
    print("\n[4/6] Checking network bridge...")
    ok, data = pve_request(f"/nodes/{node}/network", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT) if api_ok else (False, "auth skipped")
    if not ok:
        print(f"  WARN — Network check skipped: {data}")
    else:
        bridges = [n["iface"] for n in data if n.get("type") == "bridge"] if isinstance(data, list) else []
        if bridge_name in bridges:
            print(f"  OK — Bridge '{bridge_name}' exists on node {node}")
        else:
            print(f"  FAIL — Bridge '{bridge_name}' not found. Available bridges: {', '.join(bridges) or 'none'}")

    # 5. Build source
    print("\n[5/6] Checking build source...")
    template_vmid = build_source.get("template_vmid")
    iso_path = build_source.get("iso_path")
    create_blank = build_source.get("create_blank", True)
    if template_vmid:
        ok, data = pve_request(f"/nodes/{node}/qemu/{template_vmid}/status/current", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT) if api_ok else (False, "auth skipped")
        if not ok:
            if not api_ok:
                print(f"  WARN — Cannot verify template (auth skipped)")
            else:
                ok2, _ = pve_request("/cluster/resources?type=vm", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT)
                vmids = []
                if ok2 and isinstance(_, list):
                    vmids = [r["vmid"] for r in _ if r.get("type") == "qemu"]
                print(f"  FAIL — Template VMID {template_vmid} not found or inaccessible. VMs: {vmids}")
                sys.exit(1)
        else:
            print(f"  OK — Template VMID {template_vmid} exists")
    elif iso_path:
        # Parse storage:path
        if ":" in iso_path:
            iso_storage, iso_file = iso_path.split(":", 1)
            ok, data = pve_request(f"/nodes/{node}/storage/{iso_storage}/content", creds=creds, host=PROXMOX_HOST, port=PROXMOX_PORT) if api_ok else (False, "auth skipped")
            if not ok:
                print(f"  WARN — Cannot list storage {iso_storage}: {data}")
            else:
                vols = [v.get("volid", "") for v in data if isinstance(data, list)]
                if any(iso_path in v or iso_file in v for v in vols):
                    print(f"  OK — ISO at {iso_path} found")
                else:
                    print(f"  WARN — ISO {iso_path} not found in storage. Volumes: {vols[:5]}...")
        else:
            print(f"  WARN — iso_path should be storage:path format (e.g. local:iso/foo.iso)")
    elif create_blank:
        print(f"  OK — create_blank=true; will create blank VMs (manual Windows install required)")
    else:
        print(f"  FAIL — No build source: set template_vmid, iso_path, or create_blank=true")
        sys.exit(1)

    # 6. Guest OS decision gate
    print("\n[6/6] Guest OS feasibility gate...")
    macos_ok, macos_reason = feasibility_gate_macos()
    if macos_ok:
        guest_os = "macos"
        print("  Decision: macOS (if Proxmox host is Apple hardware)")
    else:
        guest_os = "windows"
        print(f"  Decision: Windows (macOS not feasible: {macos_reason})")

    # Update config if requested
    if args.update_config and CONFIG_PATH.exists():
        content = CONFIG_PATH.read_text()
        if "guest_os:" in content:
            import re
            content = re.sub(r'guest_os:\s*["\']?\w+["\']?', f'guest_os: "{guest_os}"', content)
        else:
            content = content.replace("proxmox:", f'guest_os: "{guest_os}"\n\nproxmox:')
        CONFIG_PATH.write_text(content)
        print(f"\n  Updated {CONFIG_PATH} with guest_os: {guest_os}")

    print("\n" + "=" * 60)
    print("  Validation complete. Guest OS: Windows")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
