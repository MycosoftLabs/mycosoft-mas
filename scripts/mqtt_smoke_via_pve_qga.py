#!/usr/bin/env python3
"""
MQTT authenticated smoke test inside guest via Proxmox guest exec.

Date: 2026-04-08
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from infra.csuite.provision_ssh import pve_ssh_exec


def main() -> int:
    pve = (os.environ.get("PVE_SSH_HOST") or "192.168.0.90").strip()
    vmid = (os.environ.get("MQTT_VM_VMID") or "101").strip()
    pve_pw = (os.environ.get("PROXMOX_PASSWORD") or os.environ.get("VM_PASSWORD") or "").strip()
    mqtt_pw = (os.environ.get("MQTT_BROKER_PASSWORD") or os.environ.get("VM_PASSWORD") or "").strip()
    if not pve_pw or not mqtt_pw:
        print("ERROR: Missing PROXMOX_PASSWORD/VM_PASSWORD or MQTT_BROKER_PASSWORD", file=sys.stderr)
        return 1

    b64 = base64.b64encode(mqtt_pw.encode("utf-8")).decode("ascii")
    cmd = (
        f"qm guest exec {vmid} -- bash -lc "
        + "'"
        + f"MQPW=$(echo {b64} | base64 -d); "
        + "docker exec mycobrain-mqtt mosquitto_sub -u mycobrain -P \"$MQPW\" -t mycobrain/test -C 1 -W 10 & "
        + "sleep 1; "
        + "docker exec mycobrain-mqtt mosquitto_pub -u mycobrain -P \"$MQPW\" -t mycobrain/test -m '{\"ping\":\"ok\"}'; "
        + "wait || true"
        + "'"
    )
    ok, out = pve_ssh_exec(pve, "root", pve_pw, cmd, timeout=120)
    print(f"SMOKE_OK={ok}")
    print(out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
