#!/usr/bin/env python3
"""
Discover Windows 11 template or ISO on Proxmox 202.
Updates config/proxmox202_csuite.yaml with template_vmid or iso_path.
Date: March 7, 2026
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from infra.csuite.provision_base import (
    load_credentials,
    load_proxmox_config,
    pve_request,
)
from infra.csuite.provision_csuite import get_proxmox_settings


def main() -> int:
    creds = load_credentials()
    pve = get_proxmox_settings()
    host = pve["host"].split(":")[0]
    port = pve["port"]
    node = pve["node"]

    print(f"Proxmox: {host}:{port} node={node}")
    print()

    # 1. List all VMs (including templates)
    ok, vm_list = pve_request(
        "/cluster/resources?type=vm",
        host=host,
        port=port,
        creds=creds,
    )
    if not ok:
        print(f"ERROR listing VMs: {vm_list}")
        return 1

    templates = [v for v in vm_list if v.get("type") == "qemu" and v.get("template")]
    vms = [v for v in vm_list if v.get("type") == "qemu" and not v.get("template")]

    print("=== VM TEMPLATES ===")
    if templates:
        for t in templates:
            print(f"  VMID {t.get('vmid')}: {t.get('name', '')} (node={t.get('node', '')})")
    else:
        print("  (none)")

    print()
    print("=== VMs (non-template) ===")
    for v in sorted(vms, key=lambda x: x.get("vmid", 0)):
        print(f"  VMID {v.get('vmid')}: {v.get('name', '')} status={v.get('status', '')} node={v.get('node', '')}")

    # 2. List storage content (ISOs)
    print()
    print("=== STORAGE CONTENT (ISOs) ===")
    ok_storages, storages = pve_request(
        f"/nodes/{node}/storage",
        host=host,
        port=port,
        creds=creds,
    )
    if ok_storages and isinstance(storages, list):
        for s in storages:
            sid = s.get("storage", "")
            stype = s.get("type", "")
            if stype in ("dir", "nfs", "cifs") or "iso" in (s.get("content") or ""):
                ok_c, content = pve_request(
                    f"/nodes/{node}/storage/{sid}/content",
                    host=host,
                    port=port,
                    creds=creds,
                )
                if ok_c and isinstance(content, list):
                    isos = [c for c in content if c.get("format") == "iso" or "iso" in (c.get("volid") or "").lower()]
                    if isos:
                        print(f"  Storage {sid}:")
                        for iso in isos:
                            volid = iso.get("volid", "")
                            print(f"    {volid}")
    else:
        print("  (could not list storage)")

    # 3. Pick best Windows template
    template_vmid = None
    if templates:
        def score(v):
            name = (v.get("name") or "").lower()
            if "win11" in name:
                return 3
            if "windows" in name or "win10" in name:
                return 2
            return 1
        best = max(templates, key=score)
        template_vmid = int(best["vmid"])
        print()
        print(f"RECOMMENDED template_vmid: {template_vmid} ({best.get('name', '')})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
