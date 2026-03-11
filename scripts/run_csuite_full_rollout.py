#!/usr/bin/env python3
"""
C-Suite full rollout — resource check, provision all VMs, bootstrap OpenClaw.

1. Check Proxmox 202 connectivity and resources (API or SSH fallback)
2. Discover Windows template if present
3. Provision CEO -> CTO -> CFO -> COO (create or clone)
4. Bootstrap each with OpenClaw, role manifest, heartbeat

When Proxmox API returns 401, automatically falls back to SSH (root@host with
VM_PASSWORD / PROXMOX202_PASSWORD). All VM operations then use qm/pvesh via SSH.

Usage:
  python scripts/run_csuite_full_rollout.py
  python scripts/run_csuite_full_rollout.py --dry-run
  python scripts/run_csuite_full_rollout.py --skip-bootstrap

Requires: PROXMOX_PASSWORD or PROXMOX_TOKEN, CSUITE_GUEST_PASSWORD or VM_PASSWORD
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("csuite-rollout")


def load_config():
    import yaml
    cfg_path = REPO_ROOT / "config" / "proxmox202_csuite.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_proxmox202_credentials() -> bool:
    """
    Ensure PROXMOX202_PASSWORD is available for Proxmox 202 root auth.
    If not set, copy from VM_PASSWORD (per vm-credentials: same password across systems).
    Returns True if we have credentials to try.
    """
    from infra.csuite.provision_base import load_credentials as _load
    creds = _load()
    if creds.get("proxmox202_password") or creds.get("proxmox_password"):
        return True
    vm_pwd = creds.get("vm_password") or ""
    if not vm_pwd:
        return False
    # Ensure PROXMOX202_PASSWORD in env for this run (fallback chain uses it)
    os.environ.setdefault("PROXMOX202_PASSWORD", vm_pwd)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="C-Suite full rollout on Proxmox 202")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no VM creation")
    parser.add_argument("--skip-bootstrap", action="store_true", help="Create VMs but skip WinRM bootstrap")
    args = parser.parse_args()

    cfg = load_config()
    pve = cfg.get("proxmox", {})
    host = pve.get("host", "192.168.0.202")
    port = int(pve.get("port", 8006))
    node = pve.get("node", "pve")
    spec = cfg.get("vm_spec", {})
    cores_per = spec.get("cores", 4)
    mem_mb_per = spec.get("memory_mb", 16384)
    disk_gb_per = spec.get("disk_gb", 128)
    vms = cfg.get("vms", {})
    n_vms = len(vms)
    total_cores = n_vms * cores_per
    total_mem_mb = n_vms * mem_mb_per
    total_disk_gb = n_vms * disk_gb_per

    # Ensure Proxmox 202 credentials: persist to .credentials.local if missing, then set env
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "ensure_proxmox202_credentials.py")], cwd=str(REPO_ROOT), check=False)
    ensure_proxmox202_credentials()

    print("=" * 60)
    print("  C-Suite Full Rollout — Proxmox 202")
    print(f"  Target: {host}:{port} node={node}")
    print(f"  VMs: {n_vms} (CEO, CTO, CFO, COO)")
    print(f"  Required: {total_cores} cores, {total_mem_mb // 1024} GB RAM, {total_disk_gb} GB disk")
    print("=" * 60)

    # Step 1: Validate Proxmox 202 — try API first, fall back to SSH on 401
    from infra.csuite.provision_base import (
        load_credentials,
        load_proxmox_config,
        discover_windows_template,
        pve_delete_vm,
        pve_request,
    )
    from infra.csuite.provision_ssh import (
        pve_ssh_status,
        pve_ssh_list_resources,
        pve_ssh_discover_windows_template,
        pve_ssh_delete_vm,
    )

    creds = load_credentials()
    # Build list of passwords to try (dedupe, non-empty) — API and SSH will try each
    _pwds = [
        creds.get("proxmox202_password"),
        creds.get("proxmox_password"),
        creds.get("vm_password"),
    ]
    ssh_passwords = list(dict.fromkeys(p for p in _pwds if (p or "").strip()))
    ssh_pwd = ssh_passwords[0] if ssh_passwords else ""
    has_pwd = creds.get("proxmox_password") or creds.get("proxmox202_password")
    has_token = creds.get("proxmox_token") or creds.get("proxmox202_token")
    if not has_token and not has_pwd and not ssh_pwd:
        logger.info("No password/token in env — will try SSH key auth (root@%s)", host)

    use_ssh = False
    ok, data = pve_request(
        f"/nodes/{node}/status",
        host=host,
        port=port,
        creds=creds,
    )
    if not ok:
        if "401" in str(data) or "403" in str(data) or "Auth failed" in str(data) or "Permission check failed" in str(data):
            logger.info("Proxmox API auth/permission failed (401/403) — trying SSH fallback (root@%s)", host)
            ssh_err = "no password to try"
            # 1) Try SSH key auth first (config/proxmox202_id_rsa, ~/.ssh/id_*, agent) — no password
            ssh_ok, ssh_data = pve_ssh_status(host, node, "root", "")
            if ssh_ok:
                use_ssh = True
                data = ssh_data
                os.environ["CSUITE_USE_SSH"] = "1"
                logger.info("SSH fallback OK (key auth) — using qm/pvesh via SSH for all Proxmox operations")
            else:
                ssh_err = ssh_data
            # 2) Try each password
            if not use_ssh and ssh_passwords:
                for pwd in ssh_passwords:
                    ssh_ok, ssh_data = pve_ssh_status(host, node, "root", pwd or "")
                    if ssh_ok:
                        use_ssh = True
                        ssh_pwd = pwd or ""
                        data = ssh_data
                        os.environ["CSUITE_USE_SSH"] = "1"
                        os.environ["CSUITE_SSH_PASSWORD"] = ssh_pwd
                        logger.info("SSH fallback OK (password) — using qm/pvesh via SSH for all Proxmox operations")
                        break
                    ssh_err = ssh_data
            if not use_ssh:
                logger.error("SSH fallback failed for all %d password(s): %s", len(ssh_passwords), ssh_err)
                logger.error("Add PROXMOX202_PASSWORD or VM_PASSWORD to .credentials.local, or configure SSH key for root@%s", host)
                return 1
        else:
            logger.error("Proxmox 202 unreachable or auth failed: %s", data)
            return 1

    mem_total = data.get("memory", {}).get("total", 0)
    mem_used = data.get("memory", {}).get("used", 0)
    mem_free_mb = (mem_total - mem_used) // (1024 * 1024)
    cpu_total = float(data.get("cpuinfo", {}).get("cpus", 1))

    print("\n[1/4] Proxmox 202 resource check" + (" (SSH)" if use_ssh else " (API)"))
    print(f"  Node: {node}")
    print(f"  Memory: {mem_free_mb} MB free (need {total_mem_mb} MB for {n_vms} VMs)")
    print(f"  CPU: {cpu_total} cores available")

    if mem_free_mb < total_mem_mb:
        logger.warning("  WARN — Free RAM (%d MB) < required (%d MB). VMs may not all start.", mem_free_mb, total_mem_mb)
    else:
        print("  OK — Sufficient RAM")

    # List VMs and discover Windows template
    if use_ssh:
        ok2, vm_list = pve_ssh_list_resources(host, "root", ssh_pwd)
        if not ok2:
            logger.error("Failed to list VMs via SSH: %s", vm_list)
            return 1
        qemu = [v for v in (vm_list or []) if isinstance(v, dict) and v.get("type") == "qemu"]
    else:
        ok2, vm_list = pve_request(
            "/cluster/resources?type=vm",
            host=host,
            port=port,
            creds=creds,
        )
        qemu = [v for v in (vm_list or []) if isinstance(v, dict) and v.get("type") == "qemu"]
    existing_vmids = {int(v["vmid"]) for v in qemu}
    print(f"\n  Existing VMs: {len(qemu)}")

    # Discover Windows 11 template and update config
    if use_ssh:
        template_vmid = pve_ssh_discover_windows_template(host, "root", ssh_pwd)
    else:
        template_vmid = discover_windows_template(host=host, port=port, node=node, creds=creds)
    if template_vmid:
        logger.info("Discovered Windows template: VMID %d", template_vmid)
        print(f"  Windows template: VMID {template_vmid}")
        cfg_path = REPO_ROOT / "config" / "proxmox202_csuite.yaml"
        if cfg_path.exists():
            import yaml
            cfg = load_proxmox_config(cfg_path)
            if "build_source" not in cfg:
                cfg["build_source"] = {}
            cfg["build_source"]["template_vmid"] = template_vmid
            cfg["build_source"]["create_blank"] = False
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            logger.info("Updated config with template_vmid=%d", template_vmid)
            # If CEO (192) exists but was created blank, delete it so we recreate from template
            ceo_vmid = vms.get("ceo", {}).get("vmid", 192)
            if ceo_vmid in existing_vmids and template_vmid:
                logger.info("Recreating CEO VM %d from template (was blank)", ceo_vmid)
                if use_ssh:
                    ok_del, msg = pve_ssh_delete_vm(host, ceo_vmid, "root", ssh_pwd, stop_first=True)
                else:
                    ok_del, msg = pve_delete_vm(node, ceo_vmid, host, port, creds, stop_first=True)
                if ok_del:
                    logger.info("Deleted CEO VM %d; will recreate from template", ceo_vmid)
                else:
                    logger.warning("Could not delete CEO VM %d: %s — provision may use existing blank VM", ceo_vmid, msg)
    else:
        print("  No Windows template found — CEO will be created blank if template_vmid not set in config")

    # Step 2: Run validation script (uses Proxmox 202 from config now)
    print("\n[2/4] Running feasibility validation...")
    val_script = REPO_ROOT / "scripts" / "validate_proxmox202_feasibility.py"
    if not val_script.exists():
        val_script = REPO_ROOT / "scripts" / "validate_proxmox90_feasibility.py"
    if val_script.exists():
        rc = subprocess.run([sys.executable, str(val_script)], cwd=str(REPO_ROOT))
        if rc.returncode != 0 and not args.dry_run:
            logger.warning("Validation had issues; continuing anyway")
    else:
        print("  (validation script not found — skipping)")

    if args.dry_run:
        print("\n[DRY RUN] Would provision all VMs and run bootstrap. Exiting.")
        return 0

    # Step 3: Provision all VMs
    print("\n[3/4] Provisioning VMs (CEO -> CTO -> CFO -> COO)...")
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "provision_csuite_vm.py"), "--role", "all"]
    if args.skip_bootstrap:
        pass
    else:
        cmd.append("--bootstrap")
    rc = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if rc.returncode != 0:
        logger.error("Provisioning failed (exit %d)", rc.returncode)
        return rc.returncode

    print("\n[4/4] Rollout complete")
    print("  CEO (Atlas): 192.168.0.192 — MYCAOS")
    print("  CTO (Forge): 192.168.0.194 — Cursor")
    print("  CFO (Meridian): 192.168.0.193 — Perplexity")
    print("  COO (Nexus): 192.168.0.195 — Claude Cowork")
    print("\n  Each VM: OpenClaw + role-specific apps + heartbeat to MAS")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
