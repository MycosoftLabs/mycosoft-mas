"""SSH to MAS VM 188: start Prometheus container if stopped; allow UFW 9090 from LAN.

Reads VM password like diagnose_prometheus_mas188.py (env → MYCO_SOFT_CREDENTIALS_FILE → .credentials.local).

  cd mycosoft-mas
  python scripts/remediate_prometheus_mas188.py
"""
from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
CRED = REPO / ".credentials.local"
MAS_IP = "192.168.0.188"
USER = "mycosoft"


def load_vm_password() -> str:
    for env_key in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
        v = os.environ.get(env_key, "").strip()
        if v:
            return v
    cred_path = os.environ.get("MYCO_SOFT_CREDENTIALS_FILE", "").strip()
    paths = [Path(cred_path).expanduser() if cred_path else None, CRED]
    for p in paths:
        if not p or not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for key in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                m = re.match(rf"^\s*{key}\s*=\s*(.+)\s*$", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
    raise SystemExit(
        "No VM password: set VM_PASSWORD or MYCO_SOFT_CREDENTIALS_FILE; "
        "see docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md"
    )


def run_shell(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", errors="replace")
    e = err.read().decode("utf-8", errors="replace")
    code = out.channel.recv_exit_status()
    return code, o, e


def sudo_bash(ssh: paramiko.SSHClient, pw: str, inner: str, timeout: int = 120) -> tuple[int, str, str]:
    quoted = shlex.quote(inner)
    cmd = f"sudo -S -p '' bash -c {quoted}"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdin.write(pw + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    o = stdout.read().decode("utf-8", errors="replace")
    e = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, o, e


def main() -> None:
    pw = load_vm_password()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(MAS_IP, username=USER, password=pw, timeout=25)

    code, o, e = run_shell(
        ssh,
        "docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -iE 'prometheus|^prom\\t' || true",
    )
    print("=== docker prometheus-like ===")
    print(o.rstrip() or "(none matched)")

    code, o, e = run_shell(ssh, r"docker ps -a --format '{{.Names}}\t{{.State.Status}}'")
    names_stopped: list[str] = []
    for line in o.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and "prometheus" in parts[0].lower() and parts[1] != "running":
            names_stopped.append(parts[0])

    for name in names_stopped:
        code, o, e = run_shell(ssh, f"docker start {shlex.quote(name)}")
        print(f"docker start {name} exit={code} out={o.strip()} err={e.strip()[:200]}")

    def localhost_health() -> str:
        _, o, _ = run_shell(
            ssh,
            "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "
            "http://127.0.0.1:9090/-/healthy || echo FAIL",
        )
        return o.strip()

    health = localhost_health()
    print(f"=== localhost /-/healthy === {health}")

    if health != "200":
        print("=== bootstrap: docker compose up prometheus (~/mycosoft/mas) ===")
        bootstrap = (
            "cd ~/mycosoft/mas && "
            "(docker compose version >/dev/null 2>&1 && docker compose up -d prometheus || "
            "docker-compose up -d prometheus) 2>&1"
        )
        code, o, e = run_shell(ssh, bootstrap, timeout=600)
        print(o[-4000:] if len(o) > 4000 else o)
        if e.strip():
            print("stderr:", e.strip()[:1500])
        health = localhost_health()
        print(f"=== localhost /-/healthy (after compose) === {health}")

    if health == "200":
        code, o, e = sudo_bash(
            ssh,
            pw,
            "command -v ufw >/dev/null 2>&1 && ufw allow from 192.168.0.0/24 to any port 9090 proto tcp "
            "comment mycosoft-prometheus-lan || true",
        )
        print(f"=== ufw allow 9090 exit={code} ===")
        print(o.strip()[:1500])
        if e.strip():
            print("stderr:", e.strip()[:800])
        sudo_bash(ssh, pw, "command -v ufw >/dev/null 2>&1 && ufw reload || true")

    ssh.close()


if __name__ == "__main__":
    main()
