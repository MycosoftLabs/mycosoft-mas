#!/usr/bin/env python3
"""
Push mycobrain-mqtt-prod into the MQTT guest via Proxmox qm guest exec (no guest SSH).

Requires: QEMU guest agent running in the VM; Proxmox root SSH (VM_PASSWORD / PROXMOX_PASSWORD).

Env:
  PVE_SSH_HOST           default 192.168.0.90
  MQTT_VM_VMID           default 101
  MQTT_BROKER_PASSWORD   default VM_PASSWORD
  VM_PASSWORD / PROXMOX_PASSWORD for root@PVE

Date: 2026-04-08
"""
from __future__ import annotations

import base64
import io
import os
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from infra.csuite.provision_base import load_credentials  # noqa: E402
from infra.csuite.provision_ssh import pve_ssh_exec  # noqa: E402


def _make_tar(bundle: Path) -> bytes:
    buf = io.BytesIO()
    root = "opt/mycobrain/mqtt-broker"
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(bundle / "docker-compose.yml", arcname=f"{root}/docker-compose.yml")
        tf.add(bundle / "config" / "mosquitto.conf", arcname=f"{root}/config/mosquitto.conf")
        tf.add(bundle / "config" / "passwd", arcname=f"{root}/config/passwd")
    return buf.getvalue()


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("ERROR: pip install paramiko", file=sys.stderr)
        return 1

    vmid = int(os.environ.get("MQTT_VM_VMID", "101"))
    pve = (os.environ.get("PVE_SSH_HOST") or "192.168.0.90").strip()
    creds = load_credentials()
    pve_pw = (
        (os.environ.get("PROXMOX_PASSWORD") or "").strip()
        or creds.get("proxmox_password")
        or creds.get("proxmox202_password")
        or creds.get("vm_password")
        or ""
    ).strip()
    vm_pw = (
        (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
        or creds.get("vm_password")
        or ""
    ).strip()
    # Broker user password (mosquitto); optional override separate from guest SSH
    mqtt_pw = (os.environ.get("MQTT_BROKER_PASSWORD") or "").strip() or vm_pw

    if not pve_pw:
        print("ERROR: Proxmox SSH password (PROXMOX_PASSWORD / .credentials.local)", file=sys.stderr)
        return 1
    if not mqtt_pw:
        print("ERROR: MQTT_BROKER_PASSWORD or VM_PASSWORD", file=sys.stderr)
        return 1

    def _out(s: str) -> None:
        sys.stdout.buffer.write((s + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    # CODE/mycobrain/MQTT/mycobrain-mqtt-prod (sibling of CODE/MAS/mycosoft-mas)
    bundle = REPO.parent.parent / "mycobrain" / "MQTT" / "mycobrain-mqtt-prod"
    if not bundle.is_dir():
        print(f"ERROR: Bundle not found: {bundle}", file=sys.stderr)
        return 1

    passwd = bundle / "config" / "passwd"
    passwd.parent.mkdir(parents=True, exist_ok=True)
    if not passwd.exists():
        passwd.write_bytes(b"")

    raw = _make_tar(bundle)
    b64 = base64.b64encode(raw).decode("ascii")
    chunk = 720
    lines = [b64[i : i + chunk] for i in range(0, len(b64), chunk)]

    ok, ping = pve_ssh_exec(pve, "root", pve_pw, f"qm guest exec {vmid} -- hostname", timeout=60)
    if not ok or "QEMU guest agent is not running" in ping:
        print("ERROR: qm guest exec failed (guest agent down?). Output:\n", ping, file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile("w", suffix=".lines.txt", delete=False, encoding="ascii") as f:
        for ln in lines:
            f.write(ln + "\n")
        local_lines = f.name

    remote_lines = "/root/mqtt_bundle_b64.lines"
    try:
        t = paramiko.Transport((pve, 22))
        t.start_client(timeout=30)
        t.auth_password("root", pve_pw)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.put(local_lines, remote_lines)
        sftp.close()
        t.close()
    except Exception as e:
        print(f"ERROR: SFTP to PVE failed: {e}", file=sys.stderr)
        return 1
    finally:
        Path(local_lines).unlink(missing_ok=True)

    push_py = r"""import subprocess, sys
vmid, path = sys.argv[1], sys.argv[2]
subprocess.run(
    ["qm", "guest", "exec", vmid, "--", "bash", "-lc", "rm -f /tmp/mqtt_b64_on_guest"],
    check=False,
)
with open(path, encoding="ascii") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        inner = "echo -n " + repr(line) + " >> /tmp/mqtt_b64_on_guest"
        subprocess.run(["qm", "guest", "exec", vmid, "--", "bash", "-lc", inner], check=True)
subprocess.run(
    [
        "qm",
        "guest",
        "exec",
        vmid,
        "--",
        "bash",
        "-lc",
        "base64 -d /tmp/mqtt_b64_on_guest | tar xz -C / && rm -f /tmp/mqtt_b64_on_guest",
    ],
    check=True,
)
"""
    ok, out = pve_ssh_exec(
        pve,
        "root",
        pve_pw,
        f"cat > /root/mqtt_push_bundle.py <<'PYEOF'\n{push_py}\nPYEOF\n"
        f"python3 /root/mqtt_push_bundle.py {vmid} {remote_lines}\n"
        f"rm -f /root/mqtt_push_bundle.py {remote_lines}\n",
        timeout=3600,
    )
    _out(out)
    if not ok:
        print("ERROR: bundle transfer via guest agent failed.", file=sys.stderr)
        return 1

    mq_b64 = base64.b64encode(mqtt_pw.encode("utf-8")).decode("ascii")
    setup = f"""set -euo pipefail
VMID={vmid}
qm guest exec "$VMID" -- bash -lc 'export DEBIAN_FRONTEND=noninteractive; apt-get update -y; apt-get install -y docker.io docker-compose-v2; systemctl enable --now docker'
qm guest exec "$VMID" -- bash -lc 'cd /opt/mycobrain/mqtt-broker && mkdir -p log data && chown -R 1883:1883 log data 2>/dev/null || chown -R 100:101 log data 2>/dev/null || true && touch config/passwd && chown root:root config/passwd 2>/dev/null || true && chmod 644 config/passwd 2>/dev/null || true'
qm guest exec "$VMID" -- bash -lc 'cd /opt/mycobrain/mqtt-broker && docker compose pull && docker compose up -d && sleep 4'
qm guest exec "$VMID" -- bash -lc 'MQPW=$(echo {mq_b64} | base64 -d); docker exec mycobrain-mqtt mosquitto_passwd -b /mosquitto/config/passwd mycobrain "$MQPW"; docker restart mycobrain-mqtt; sleep 3'
qm guest exec "$VMID" -- bash -lc 'docker logs mycobrain-mqtt 2>&1 | tail -n 20'
"""
    ok2, out2 = pve_ssh_exec(pve, "root", pve_pw, setup, timeout=1800)
    _out(out2)
    if not ok2:
        print("ERROR: Docker/Mosquitto setup on guest failed.", file=sys.stderr)
        return 1

    _out("\nDone (guest agent path). Jetson: MYCOBRAIN_MQTT_URL=mqtt://<guest-ip>:1883 user mycobrain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
