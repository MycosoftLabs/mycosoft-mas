"""
Shared provisioning base — Proxmox API, credentials, config loading.

Used by VM 191 (MYCA workspace) and C-Suite (CEO, CFO, CTO, COO) provisioning.
Date: March 7, 2026
"""
from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("provision-base")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_credentials() -> dict[str, str]:
    """Load credentials from .credentials.local (MAS, Website), .env, ~/.mycosoft-credentials (merge all).
    Proxmox 202 uses same password as VMs per vm-credentials; fallback chain ensures it is set.
    """
    website_root = REPO_ROOT.parent / "WEBSITE" / "website"
    platform_infra = REPO_ROOT.parent / "platform-infra"
    # Load Proxmox 202–specific creds first so they override VM_PASSWORD when different
    cred_paths = [
        REPO_ROOT / "config" / "proxmox202_credentials.env",  # Proxmox 202–specific (gitignored) — first
        REPO_ROOT / ".credentials.local",
        website_root / ".credentials.local",
        platform_infra / ".credentials.local",
        REPO_ROOT / "config" / "development.env",
        REPO_ROOT / "config" / "production.env",
        REPO_ROOT / ".env",
        platform_infra / ".env",
        Path.home() / ".mycosoft-credentials",
    ]
    for p in cred_paths:
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8-sig")  # handle BOM
            except Exception as e:
                logger.warning("Could not read %s: %s", p, e)
                continue
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    key = k.strip()
                    val = v.strip().strip('"').strip("'").strip()
                    os.environ.setdefault(key, val)

    vm_pwd = os.getenv("VM_PASSWORD", "") or os.getenv("VM_SSH_PASSWORD", "")
    proxmox202_pwd = (
        os.getenv("PROXMOX202_PASSWORD", "")
        or os.getenv("PROXMOX_PASSWORD", "")
        or vm_pwd
    )
    return {
        "proxmox_token": os.getenv("PROXMOX_TOKEN", ""),
        "proxmox202_token": os.getenv("PROXMOX202_TOKEN", ""),
        "proxmox_password": os.getenv("PROXMOX_PASSWORD", "") or vm_pwd,
        "proxmox202_password": proxmox202_pwd,
        "vm_password": vm_pwd,
    }


def load_proxmox_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load Proxmox/C-Suite config from YAML."""
    import yaml
    path = config_path or (REPO_ROOT / "config" / "proxmox202_csuite.yaml")
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _pve_ticket_auth(base: str, passwords: list[str]) -> tuple[bool, dict[str, str] | str]:
    """Try password auth against /access/ticket. Returns (ok, headers_dict_or_error)."""
    for pwd in passwords:
        if not (pwd or "").strip():
            continue
        try:
            req = urllib.request.Request(
                f"{base}/access/ticket",
                data=urllib.parse.urlencode({
                    "username": "root@pam",
                    "password": pwd.strip(),
                }).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            r = urllib.request.urlopen(req, context=ctx, timeout=15)
            ticket = json.loads(r.read())["data"]
            return True, {
                "Cookie": f"PVEAuthCookie={ticket['ticket']}",
                "CSRFPreventionToken": ticket["CSRFPreventionToken"],
            }
        except urllib.error.HTTPError as e:
            if e.code == 401:
                continue
            return False, f"Auth failed: HTTP {e.code}"
        except Exception as e:
            return False, str(e)
    return False, "Auth failed: all passwords rejected (401)"


def pve_request(
    path: str,
    host: str = "192.168.0.90",
    port: int = 8006,
    node: str = "pve",
    method: str = "GET",
    data: dict | None = None,
    creds: dict | None = None,
) -> tuple[bool, Any]:
    """Call Proxmox API. Returns (ok, data_or_error_message).
    For Proxmox 202: tries token first; on 401/403 (e.g. token lacks Sys.Audit),
    retries with ticket auth (root@pam + password) which has full permissions.
    """
    creds = creds or load_credentials()
    base = f"https://{host}:{port}/api2/json"

    headers: dict[str, str] = {}
    # PROXMOX202_USE_PASSWORD=1 skips token and uses root@pam+password (full perms)
    # Use when token lacks VM.Clone/VM.Config or other required privileges
    force_password = os.getenv("PROXMOX202_USE_PASSWORD", "").strip().lower() in ("1", "true", "yes")
    use_token_first = True
    token = None if (force_password and "202" in host) else (
        (creds.get("proxmox202_token") if "202" in host else None) or creds.get("proxmox_token")
    )
    if token:
        tok = token.strip()
        if not tok.startswith("PVEAPIToken"):
            tok = f"PVEAPIToken={tok}"
        headers["Authorization"] = tok
    else:
        use_token_first = False
        pwds = []
        if "202" in host:
            pwds = [
                creds.get("proxmox202_password"),
                creds.get("proxmox_password"),
                creds.get("vm_password"),
            ]
        else:
            pwds = [creds.get("proxmox_password"), creds.get("proxmox202_password"), creds.get("vm_password")]
        pwds = [p for p in pwds if p]
        if not pwds:
            return False, "No Proxmox credentials (PROXMOX_TOKEN, PROXMOX_PASSWORD, or PROXMOX202_PASSWORD)"
        ok_auth, auth_result = _pve_ticket_auth(base, pwds)
        if not ok_auth:
            return False, auth_result
        headers.update(auth_result)

    def _do_request(hdrs: dict) -> tuple[bool, Any]:
        try:
            payload = urllib.parse.urlencode(data).encode() if data else None
            req = urllib.request.Request(
                base + path,
                data=payload,
                headers={**hdrs, "Content-Type": "application/x-www-form-urlencoded"} if payload else hdrs,
                method=method,
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            r = urllib.request.urlopen(req, context=ctx, timeout=30)
            body = r.read().decode()
            if not body:
                return True, None
            out = json.loads(body)
            return True, out.get("data", out)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            return False, (e.code, body)
        except Exception as e:
            return False, (0, str(e))

    ok, result = _do_request(headers)
    # On 401/403 with token auth, retry with ticket auth (root has full permissions)
    if not ok and use_token_first and isinstance(result, tuple) and len(result) == 2:
        code, body = result
        if code in (401, 403) and ("Permission check failed" in body or "401" in body or "403" in body):
            pwds = []
            if "202" in host:
                pwds = [
                    creds.get("proxmox202_password"),
                    creds.get("proxmox_password"),
                    creds.get("vm_password"),
                ]
            else:
                pwds = [creds.get("proxmox_password"), creds.get("proxmox202_password"), creds.get("vm_password")]
            pwds = [p for p in pwds if p]
            if pwds:
                ok_auth, auth_result = _pve_ticket_auth(base, pwds)
                if ok_auth:
                    headers = {**headers, **auth_result}
                    del headers["Authorization"]
                    ok, result = _do_request(headers)
                    if ok:
                        return ok, result
                    if isinstance(result, tuple):
                        return False, f"HTTP {result[0]}: {result[1]}"
        return False, f"HTTP {code}: {body}" if isinstance(result, tuple) else str(result)
    if not ok:
        return False, f"HTTP {result[0]}: {result[1]}" if isinstance(result, tuple) else str(result)
    return ok, result


def wait_for_port(host: str, port: int, timeout_seconds: int = 300, interval: int = 5) -> bool:
    """Wait until a port is reachable."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(interval)
    return False


def wait_for_pve_task(
    upid: str,
    node: str,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
    timeout_seconds: int = 600,
    interval_seconds: int = 5,
) -> tuple[bool, str]:
    """
    Poll a Proxmox task until it completes.
    Returns (success, message). Success is True only when status is 'stopped' and exitstatus is 'OK'.
    """
    creds = creds or load_credentials()
    # UPID format: UPID:node:pid:started:user:type:...
    start = time.time()
    while time.time() - start < timeout_seconds:
        ok, result = pve_request(
            f"/nodes/{node}/tasks/{urllib.parse.quote(upid, safe='')}/status",
            host=host,
            port=port,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        status = result.get("status", "")
        exitstatus = result.get("exitstatus", "")
        if status == "stopped":
            if exitstatus == "OK":
                return True, "Task completed"
            return False, f"Task failed: exitstatus={exitstatus}"
        time.sleep(interval_seconds)
    return False, "Task timed out"


def pve_unlock_vm(
    node: str,
    vmid: int,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
) -> tuple[bool, str]:
    """
    Clear stale lock on a VM (e.g. from failed clone). Uses config API with delete=lock, skiplock=1.
    Returns (ok, message).
    """
    creds = creds or load_credentials()
    ok, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}/config",
        host=host,
        port=port,
        method="PUT",
        data={"delete": "lock", "skiplock": 1},
        creds=creds,
    )
    if ok:
        return True, "Unlocked"
    return False, str(result)


def pve_stop_vm(
    node: str,
    vmid: int,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
    force: bool = False,
) -> tuple[bool, str]:
    """Stop a VM. Returns (ok, message). force=True uses forceStop=1 for hard stop."""
    creds = creds or load_credentials()
    data = {"forceStop": 1} if force else None
    ok, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}/status/stop",
        host=host,
        port=port,
        method="POST",
        data=data,
        creds=creds,
    )
    return ok, str(result) if not ok else "Stopped"


def pve_delete_vm(
    node: str,
    vmid: int,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
    stop_first: bool = True,
) -> tuple[bool, str]:
    """
    Delete a VM. stop_first=True stops the VM before delete (recommended).
    Returns (ok, message).
    """
    creds = creds or load_credentials()
    if stop_first:
        ok_stop, _ = pve_stop_vm(node, vmid, host, port, creds, force=True)
        if ok_stop:
            logger.info("Stopped VM %d before delete", vmid)
        time.sleep(2)
    ok, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}",
        host=host,
        port=port,
        method="DELETE",
        creds=creds,
    )
    if ok:
        return True, "Deleted"
    return False, str(result)


def discover_windows_template(
    host: str = "192.168.0.202",
    port: int = 8006,
    node: str = "pve",
    creds: dict | None = None,
) -> int | None:
    """
    Discover Windows 11 template on Proxmox via /cluster/resources?type=vm.
    Returns VMID of best match, or None if not found.
    Only considers templates (template=1). Priority: win11 > windows > any template.
    """
    creds = creds or load_credentials()
    ok, vm_list = pve_request(
        "/cluster/resources?type=vm",
        host=host,
        port=port,
        creds=creds,
    )
    if not ok or not isinstance(vm_list, list):
        return None
    templates = [v for v in vm_list if v.get("type") == "qemu" and v.get("template")]
    if not templates:
        return None

    def score(v: dict) -> int:
        """Higher = better. win11=3, windows=2, else 1."""
        name = (v.get("name") or "").lower()
        if "win11" in name:
            return 3
        if "windows" in name:
            return 2
        return 1

    best = max(templates, key=score)
    return int(best["vmid"])


def pve_get_vm_config(
    node: str,
    vmid: int,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
) -> tuple[bool, dict | str]:
    """Get VM config. Returns (ok, config_dict_or_error)."""
    creds = creds or load_credentials()
    ok, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}/config",
        host=host,
        port=port,
        creds=creds,
    )
    if not ok:
        return False, str(result)
    return True, result if isinstance(result, dict) else {}


def pve_attach_iso_and_set_boot(
    node: str,
    vmid: int,
    iso_volid: str,
    host: str = "192.168.0.90",
    port: int = 8006,
    creds: dict | None = None,
) -> tuple[bool, str]:
    """
    Attach ISO to ide2 (CD drive) and set boot order to CD first, then disk.
    iso_volid: e.g. "local:iso/Win11_24H2_English_x64.iso"
    Stops VM first if running (required for config change), then starts after.
    Returns (ok, message).
    """
    creds = creds or load_credentials()
    # ide2 format: storage:path,media=cdrom
    ide2_val = f"{iso_volid},media=cdrom"
    # Boot: CD first, then sata0 (disk) — SATA so Windows installer sees disk without drivers
    boot_order = "ide2;sata0"

    ok_stop, _ = pve_stop_vm(node, vmid, host, port, creds, force=True)
    if ok_stop:
        logger.info("Stopped VM %d before ISO attach", vmid)
        time.sleep(3)
    else:
        # VM may already be stopped
        pass

    ok, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}/config",
        host=host,
        port=port,
        method="PUT",
        data={"ide2": ide2_val, "boot": boot_order},
        creds=creds,
    )
    if not ok:
        return False, str(result)

    ok_start, _ = pve_request(
        f"/nodes/{node}/qemu/{vmid}/status/start",
        host=host,
        port=port,
        method="POST",
        creds=creds,
    )
    if not ok_start:
        return True, f"ISO attached, boot order set — VM failed to start: {result}"
    return True, f"ISO attached, boot order=ide2;sata0 — VM started. Boot from Windows installer."


def pve_clone_vm(
    node: str,
    template_vmid: int,
    newid: int,
    name: str,
    host: str = "192.168.0.90",
    port: int = 8006,
    target: str | None = None,
    full: int = 1,
    creds: dict | None = None,
) -> tuple[bool, Any]:
    """
    Clone a VM or template. Proxmox API: POST /nodes/{node}/qemu/{vmid}/clone.
    Returns (ok, data_or_error_message).
    """
    creds = creds or load_credentials()
    data: dict[str, Any] = {"newid": newid, "name": name, "full": full}
    if target:
        data["target"] = target
    ok, result = pve_request(
        f"/nodes/{node}/qemu/{template_vmid}/clone",
        host=host,
        port=port,
        method="POST",
        data=data,
        creds=creds,
    )
    return ok, result
