"""
C-Suite VM provisioning — CEO, CFO, CTO, COO on Proxmox 202.

CEO is created from the Windows 11 template; CTO/CFO/COO are cloned from the
previous role in the chain (CEO→CTO→CFO→COO). All VMs run on the same Proxmox
as MYCA workspace (VM 191).
Post-boot bootstrap (OpenClaw, etc.) is handled by the golden-image workflow.

When CSUITE_USE_SSH=1 (set by run_csuite_full_rollout when API returns 401),
all Proxmox operations use SSH (qm/pvesh) instead of the API.
Date: March 7, 2026
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from .provision_base import (
    load_credentials,
    load_proxmox_config,
    pve_clone_vm,
    pve_request,
    pve_unlock_vm,
    wait_for_port,
    wait_for_pve_task,
)
from .provision_ssh import (
    pve_ssh_clone,
    pve_ssh_create_blank_vm,
    pve_ssh_list_qemu,
    pve_ssh_start,
    pve_ssh_stop,
    pve_ssh_unlock,
    pve_ssh_set_description,
)

logger = logging.getLogger("provision-csuite")


def _use_ssh() -> bool:
    return os.environ.get("CSUITE_USE_SSH", "").strip() in ("1", "true", "yes")


def _ssh_password(creds: dict[str, str]) -> str:
    # Prefer password found during rollout (multi-password retry)
    env_pwd = os.environ.get("CSUITE_SSH_PASSWORD", "").strip()
    if env_pwd:
        return env_pwd
    return (
        creds.get("proxmox202_password")
        or creds.get("proxmox_password")
        or creds.get("vm_password")
        or ""
    )

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_role_config(role: str) -> dict[str, Any] | None:
    """Get VM config for a role (ceo, cfo, cto, coo)."""
    cfg = load_proxmox_config()
    vms = cfg.get("vms", {})
    return vms.get(role.lower())


# Rollout order for --role all: CEO first, then clone chain (CTO from CEO, CFO from CTO, COO from CFO)
ROLLOUT_ORDER = ("ceo", "cto", "cfo", "coo")


def get_all_roles() -> list[str]:
    """Return role keys in rollout order (ceo → cto → cfo → coo)."""
    cfg = load_proxmox_config()
    vms = cfg.get("vms", {})
    return [r for r in ROLLOUT_ORDER if r in vms]


def get_proxmox_settings() -> dict[str, Any]:
    """Get Proxmox host settings from config."""
    cfg = load_proxmox_config()
    pve = cfg.get("proxmox", {})
    return {
        "host": pve.get("host", "192.168.0.90"),
        "port": int(pve.get("port", 8006)),
        "node": pve.get("node", "pve"),
        "storage": pve.get("storage", "local-lvm"),
        "bridge": pve.get("bridge", "vmbr0"),
    }


def get_build_source() -> dict[str, Any]:
    """
    Get build source config (base_template_vmid, template_vmid, iso_path, ostype, create_blank).
    Resolves iso_path and ostype from windows_version: "10" uses iso_path_win10 and ostype win10;
    "11" uses iso_path and ostype win11. Default windows_version is "10" for compatibility.
    """
    cfg = load_proxmox_config()
    bs = cfg.get("build_source") or {}
    ver = str(bs.get("windows_version", "10")).strip().lower()
    if ver == "11":
        iso_path = bs.get("iso_path")
        ostype = "win11"
    else:
        iso_path = bs.get("iso_path_win10") or bs.get("iso_path")
        ostype = "win10"
    return {
        "base_template_vmid": bs.get("base_template_vmid"),
        "template_vmid": bs.get("template_vmid"),
        "iso_path": iso_path,
        "ostype": ostype,
        "create_blank": bs.get("create_blank", True),
    }


def get_vm_spec() -> dict[str, Any]:
    """Get shared VM hardware spec from config."""
    cfg = load_proxmox_config()
    return cfg.get("vm_spec", {
        "cores": 4,
        "memory_mb": 16384,
        "disk_gb": 128,
    })


def _create_windows_vm_ssh(
    role: str,
    role_cfg: dict[str, Any],
    pve: dict[str, Any],
    creds: dict[str, str],
    dry_run: bool,
    force_blank: bool = False,
) -> tuple[bool, str]:
    """Create VM via SSH (qm/pvesh) when CSUITE_USE_SSH=1."""
    vmid = role_cfg["vmid"]
    name = role_cfg["name"]
    ip = role_cfg["ip"]
    clone_from = role_cfg.get("clone_from")
    host = pve["host"].split(":")[0]
    node = pve["node"]
    user = "root"
    pwd = _ssh_password(creds)
    if not pwd:
        return False, "No SSH password: set PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local"

    # List VMs
    ok, vm_list = pve_ssh_list_qemu(host, node, user, pwd)
    if not ok:
        return False, str(vm_list)
    existing = {int(v.get("vmid", 0)): v for v in (vm_list or []) if isinstance(v, dict)}
    if vmid in existing:
        status = existing[vmid].get("status", "unknown")
        logger.info("VM %d already exists (status: %s)", vmid, status)
        if status != "running" and not dry_run:
            pve_ssh_unlock(host, vmid, user, pwd)
            ok2, msg = pve_ssh_start(host, vmid, user, pwd)
            return ok2, "Started existing VM" if ok2 else f"Failed to start VM: {msg}"
        return True, "VM already running"

    desc = f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}"
    build_source = get_build_source()
    spec = get_vm_spec()
    iso_path = build_source.get("iso_path")

    # Force blank: create new VM with ISO instead of cloning (avoids slow full clone)
    if force_blank:
        if dry_run:
            logger.info("[DRY RUN] Would create blank VM %d (%s) with ISO", vmid, name)
            return True, "Dry run — VM not created"
        storage = pve.get("storage", "local-lvm")
        bridge = pve.get("bridge", "vmbr0")
        ok, msg = pve_ssh_create_blank_vm(
            host=host,
            vmid=vmid,
            name=name,
            spec=spec,
            storage=storage,
            bridge=bridge,
            iso_path=iso_path,
            description=desc,
            user=user,
            password=pwd,
            ostype=build_source.get("ostype", "win10"),
        )
        if not ok:
            return False, msg
        return True, f"VM {vmid} ({name}) created and started. IP: {ip} — Windows install required via Proxmox console."

    # Prefer neutral base template when set (avoids role contamination; see CSUITE_NEUTRAL_BASE_IMAGE_STRATEGY)
    build_source = get_build_source()
    base_vmid = build_source.get("base_template_vmid")
    if base_vmid is not None:
        source_vmid = int(base_vmid)
        if dry_run:
            logger.info("[DRY RUN] Would clone VM %d from neutral base %d as %s", vmid, source_vmid, name)
            return True, "Dry run — VM not created"
        pve_ssh_unlock(host, source_vmid, user, pwd)
        pve_ssh_stop(host, source_vmid, user, pwd)
        time.sleep(2)
        ok, msg = pve_ssh_clone(host, source_vmid, vmid, name, user, pwd, full=1)
        pve_ssh_start(host, source_vmid, user, pwd)
        if not ok:
            return False, str(msg)
        pve_ssh_set_description(host, vmid, desc, user, pwd)
        ok2, msg2 = pve_ssh_start(host, vmid, user, pwd)
        if not ok2:
            return True, f"VM cloned but failed to start: {msg2}"
        return True, f"VM {vmid} ({name}) cloned from neutral base {source_vmid} and started. IP: {ip}"

    # Clone-from-previous-role (legacy chain: CEO→CTO→CFO→COO)
    if clone_from is not None:
        source_vmid = int(clone_from)
        if dry_run:
            logger.info("[DRY RUN] Would clone VM %d from %d as %s", vmid, source_vmid, name)
            return True, "Dry run — VM not created"
        pve_ssh_unlock(host, source_vmid, user, pwd)
        pve_ssh_stop(host, source_vmid, user, pwd)
        time.sleep(2)
        ok, msg = pve_ssh_clone(host, source_vmid, vmid, name, user, pwd, full=1)
        pve_ssh_start(host, source_vmid, user, pwd)
        if not ok:
            return False, str(msg)
        pve_ssh_set_description(host, vmid, desc, user, pwd)
        ok2, msg2 = pve_ssh_start(host, vmid, user, pwd)
        if not ok2:
            return True, f"VM cloned but failed to start: {msg2}"
        return True, f"VM {vmid} ({name}) cloned from {source_vmid} and started. IP: {ip}"

    # Clone from template
    build_source = get_build_source()
    template_vmid = build_source.get("template_vmid")
    if not template_vmid:
        return False, "No template_vmid in config — run rollout to discover Windows template first"
    if dry_run:
        logger.info("[DRY RUN] Would clone VM %d from template %d as %s", vmid, template_vmid, name)
        return True, "Dry run — VM not created"
    ok, msg = pve_ssh_clone(host, int(template_vmid), vmid, name, user, pwd, full=1)
    if not ok:
        return False, str(msg)
    pve_ssh_set_description(host, vmid, desc, user, pwd)
    ok2, msg2 = pve_ssh_start(host, vmid, user, pwd)
    if not ok2:
        return True, f"VM cloned but failed to start: {msg2}"
    return True, f"VM {vmid} ({name}) cloned from template {template_vmid} and started. IP: {ip}"


def create_windows_vm(
    role: str,
    dry_run: bool = False,
    force_blank: bool = False,
) -> tuple[bool, str]:
    """
    Create a Windows VM for the given role on Proxmox 202.
    CEO: create from template (or blank). CTO/CFO/COO: clone from previous role.
    When CSUITE_USE_SSH=1, uses SSH (qm/pvesh) instead of API.
    Returns (success, message).
    """
    role_cfg = get_role_config(role)
    if not role_cfg:
        return False, f"Unknown role: {role}"

    pve = get_proxmox_settings()
    spec = get_vm_spec()
    creds = load_credentials()

    if _use_ssh():
        return _create_windows_vm_ssh(role, role_cfg, pve, creds, dry_run, force_blank)

    vmid = role_cfg["vmid"]
    name = role_cfg["name"]
    ip = role_cfg["ip"]
    clone_from = role_cfg.get("clone_from")

    logger.info("Creating VM %d (%s) for role %s", vmid, name, role)

    # List VMs to check if this one exists
    ok_list, vm_list = pve_request(
        f"/nodes/{pve['node']}/qemu",
        host=pve["host"],
        port=pve["port"],
        creds=creds,
    )
    if not ok_list:
        return False, str(vm_list)
    existing = {v["vmid"]: v for v in (vm_list if isinstance(vm_list, list) else [])}
    if vmid in existing:
        status = existing[vmid].get("status", "unknown")
        logger.info("VM %d already exists (status: %s)", vmid, status)
        if status != "running" and not dry_run:
            # Unlock first in case of stale lock from prior failed clone
            pve_unlock_vm(pve["node"], vmid, pve["host"], pve["port"], creds)
            ok2, _ = pve_request(
                f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
                host=pve["host"],
                port=pve["port"],
                method="POST",
                creds=creds,
            )
            return ok2, "Started existing VM" if ok2 else "Failed to start VM"
        return True, "VM already running"

    # Force blank: create new VM with ISO instead of cloning (API path)
    if force_blank:
        build_source = get_build_source()
        spec = get_vm_spec()
        iso_path = build_source.get("iso_path")
        boot_order = "order=ide2;sata0" if iso_path else "order=sata0"
        vm_config = {
            "vmid": vmid,
            "name": name,
            "description": f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}",
            "cores": spec.get("cores", 4),
            "memory": spec.get("memory_mb", 16384),
            "sockets": 1,
            "cpu": "host",
            "ostype": "win11",
            "agent": 1,
            "onboot": 1,
            "sata0": f"{pve['storage']}:{spec.get('disk_gb', 128)},discard=on",
            "net0": f"virtio,bridge={pve.get('bridge', 'vmbr0')}",
            "boot": boot_order,
        }
        if iso_path:
            vm_config["ide2"] = f"{iso_path},media=cdrom"
        if dry_run:
            logger.info("[DRY RUN] Would create VM with config: %s", vm_config)
            return True, "Dry run — VM not created"
        ok, result = pve_request(
            f"/nodes/{pve['node']}/qemu",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            data=vm_config,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        ok2, _ = pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            creds=creds,
        )
        if not ok2:
            return True, f"VM created but failed to start: {result}"
        return True, f"VM {vmid} ({name}) created and started. IP: {ip} — Windows install required via Proxmox console."

    # Prefer neutral base template when set (avoids role contamination)
    build_source = get_build_source()
    base_vmid = build_source.get("base_template_vmid")
    if base_vmid is not None:
        source_vmid = int(base_vmid)
        desc = f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}"
        if dry_run:
            logger.info("[DRY RUN] Would clone VM %d from neutral base %d as %s", vmid, source_vmid, name)
            return True, "Dry run — VM not created"
        unlock_ok, _ = pve_unlock_vm(pve["node"], source_vmid, pve["host"], pve["port"], creds)
        if unlock_ok:
            logger.info("Unlocked base template VM %d", source_vmid)
        ok, result = pve_clone_vm(
            node=pve["node"],
            template_vmid=source_vmid,
            newid=vmid,
            name=name,
            host=pve["host"],
            port=pve["port"],
            target=pve.get("node"),
            full=1,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        upid = result if isinstance(result, str) and result.startswith("UPID:") else None
        if upid:
            wait_ok, wait_msg = wait_for_pve_task(
                upid, pve["node"], pve["host"], pve["port"], creds, timeout_seconds=1800
            )
            if not wait_ok:
                return False, f"Clone task failed: {wait_msg}"
        pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/config",
            host=pve["host"],
            port=pve["port"],
            method="PUT",
            data={"description": desc},
            creds=creds,
        )
        ok2, _ = pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            creds=creds,
        )
        if not ok2:
            return True, f"VM cloned but failed to start: {result}"
        return True, f"VM {vmid} ({name}) cloned from neutral base {source_vmid} and started. IP: {ip}"

    # Clone-from-previous-role path (legacy: CTO from CEO, CFO from CTO, COO from CFO)
    if clone_from is not None:
        source_vmid = int(clone_from)
        if dry_run:
            logger.info("[DRY RUN] Would clone VM %d from %d as %s", vmid, source_vmid, name)
            return True, "Dry run — VM not created"
        # Clear stale lock on source VM (e.g. from prior failed clone or timeout)
        unlock_ok, unlock_msg = pve_unlock_vm(
            pve["node"], source_vmid, pve["host"], pve["port"], creds
        )
        if unlock_ok:
            logger.info("Unlocked source VM %d", source_vmid)
        else:
            logger.warning("Could not unlock source VM %d (may be fine): %s", source_vmid, unlock_msg)
        ok, result = pve_clone_vm(
            node=pve["node"],
            template_vmid=source_vmid,
            newid=vmid,
            name=name,
            host=pve["host"],
            port=pve["port"],
            target=pve.get("node"),
            full=1,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        upid = result if isinstance(result, str) and result.startswith("UPID:") else None
        if upid:
            logger.info("Waiting for clone task %s to complete...", upid[:40])
            wait_ok, wait_msg = wait_for_pve_task(
                upid, pve["node"], pve["host"], pve["port"], creds, timeout_seconds=1800
            )
            if not wait_ok:
                return False, f"Clone task failed: {wait_msg}"
        desc = f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}"
        pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/config",
            host=pve["host"],
            port=pve["port"],
            method="PUT",
            data={"description": desc},
            creds=creds,
        )
        ok2, _ = pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            creds=creds,
        )
        if not ok2:
            return True, f"VM cloned but failed to start: {result}"
        return True, f"VM {vmid} ({name}) cloned from {source_vmid} and started. IP: {ip}"

    build_source = get_build_source()
    template_vmid = build_source.get("template_vmid")
    create_blank = build_source.get("create_blank", True)

    if template_vmid:
        # Clone from template — repeatable one-command path
        if dry_run:
            logger.info("[DRY RUN] Would clone VM %d from template %d as %s", vmid, template_vmid, name)
            return True, "Dry run — VM not created"
        ok, result = pve_clone_vm(
            node=pve["node"],
            template_vmid=int(template_vmid),
            newid=vmid,
            name=name,
            host=pve["host"],
            port=pve["port"],
            target=pve.get("node"),
            full=1,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        upid = result if isinstance(result, str) and result.startswith("UPID:") else None
        if upid:
            logger.info("Waiting for clone task %s to complete...", upid[:40])
            wait_ok, wait_msg = wait_for_pve_task(
                upid, pve["node"], pve["host"], pve["port"], creds, timeout_seconds=1800
            )
            if not wait_ok:
                return False, f"Clone task failed: {wait_msg}"
        desc = f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}"
        pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/config",
            host=pve["host"],
            port=pve["port"],
            method="PUT",
            data={"description": desc},
            creds=creds,
        )
        ok2, _ = pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            creds=creds,
        )
        if not ok2:
            return True, f"VM cloned but failed to start: {result}"
        return True, f"VM {vmid} ({name}) cloned from template {template_vmid} and started. IP: {ip}"
    elif create_blank:
        # Create blank VM — attach Windows ISO so it boots to installer
        disk_gb = spec.get("disk_gb", 128)
        iso_path = build_source.get("iso_path")
        boot_order = "order=ide2;sata0" if iso_path else "order=sata0"
        vm_config = {
            "vmid": vmid,
            "name": name,
            "description": f"C-Suite {role_cfg.get('role', role)} — {role_cfg.get('assistant_name', '')}",
            "cores": spec.get("cores", 4),
            "memory": spec.get("memory_mb", 16384),
            "sockets": 1,
            "cpu": "host",
            "ostype": "win11",
            "agent": 1,
            "onboot": 1,
            "sata0": f"{pve['storage']}:{disk_gb},discard=on",
            "net0": f"virtio,bridge={pve.get('bridge', 'vmbr0')}",
            "boot": boot_order,
        }
        if iso_path:
            vm_config["ide2"] = f"{iso_path},media=cdrom"
        if dry_run:
            logger.info("[DRY RUN] Would create VM with config: %s", vm_config)
            return True, "Dry run — VM not created"
        ok, result = pve_request(
            f"/nodes/{pve['node']}/qemu",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            data=vm_config,
            creds=creds,
        )
        if not ok:
            return False, str(result)
        ok2, _ = pve_request(
            f"/nodes/{pve['node']}/qemu/{vmid}/status/start",
            host=pve["host"],
            port=pve["port"],
            method="POST",
            creds=creds,
        )
        if not ok2:
            return True, f"VM created but failed to start: {result}"
        return True, f"VM {vmid} ({name}) created and started. IP: {ip} — Windows install required via Proxmox console."
    return False, "No build source: set template_vmid or create_blank=true in config"
