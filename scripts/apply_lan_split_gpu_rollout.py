#!/usr/bin/env python3
"""
Apply split-GPU LAN rollout: MAS .env EARTH2_API_URL + pull/restart; sandbox safe Docker prune.
Optional: probe Windows Legions (SSH) for voice/earth2 ports — firewall scripts need Admin (run locally elevated).

Reads VM_SSH_PASSWORD / VM_PASSWORD and VM IPs from repo .credentials.local.
"""
from __future__ import annotations

import os
import shlex
import sys
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise SystemExit(2)

REPO = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EARTH2_URL = "http://192.168.0.249:8220"


def load_creds() -> None:
    p = REPO / ".credentials.local"
    if not p.is_file():
        raise SystemExit(f"Missing {p}")
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def pw() -> str:
    p = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not p:
        raise SystemExit("VM_SSH_PASSWORD / VM_PASSWORD not set")
    return p


def user() -> str:
    return os.environ.get("VM_SSH_USER", "mycosoft")


def exec_plain(
    client: paramiko.SSHClient, cmd: str, timeout: float = 600
) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=int(timeout) + 60)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def apply_mas_systemd_earth2_dropin(client: paramiko.SSHClient, password: str) -> None:
    """Ensure orchestrator process always has EARTH2_API_URL (systemd does not read repo .env by default)."""
    pwq = shlex.quote(password)
    remote = f"""set -e
cat > /tmp/earth2-api.conf <<'EOF'
[Service]
Environment=EARTH2_API_URL=http://192.168.0.249:8220
EOF
echo {pwq} | sudo -S -k mkdir -p /etc/systemd/system/mas-orchestrator.service.d
echo {pwq} | sudo -S -k install -m 644 /tmp/earth2-api.conf /etc/systemd/system/mas-orchestrator.service.d/earth2-api.conf
echo {pwq} | sudo -S -k systemctl daemon-reload
"""
    code, o, e = exec_plain(client, "bash -lc " + shlex.quote(remote), timeout=120)
    print("systemd drop-in exit", code, (o + e).strip()[-800:])


def sudo_restart_mas(client: paramiko.SSHClient, password: str) -> None:
    ch = client.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S systemctl restart mas-orchestrator")
    ch.send(password + "\n")
    for _ in range(120):
        if ch.exit_status_ready():
            break
        time.sleep(0.25)
    ch.close()


def ensure_mas_earth2_env(client: paramiko.SSHClient) -> tuple[int, str, str]:
    """Idempotent EARTH2_API_URL= in MAS_DIR/.env."""
    bash = r"""
set -e
MAS_DIR="/home/mycosoft/mycosoft/mas"
[ -d "/opt/mycosoft/mas" ] && MAS_DIR="/opt/mycosoft/mas"
f="$MAS_DIR/.env"
mkdir -p "$(dirname "$f")"
touch "$f"
if grep -q '^EARTH2_API_URL=' "$f" 2>/dev/null; then
  sed -i 's|^EARTH2_API_URL=.*|EARTH2_API_URL=http://192.168.0.249:8220|' "$f"
else
  echo 'EARTH2_API_URL=http://192.168.0.249:8220' >> "$f"
fi
grep -n '^EARTH2_API_URL=' "$f" || true
echo "MAS_DIR=$MAS_DIR"
"""
    return exec_plain(client, "bash -lc " + shlex.quote(bash), timeout=60)


def deploy_mas_188() -> None:
    password = pw()
    host = os.environ.get("MAS_VM_IP", "192.168.0.188")
    print("\n=== MAS 188:", host, "===")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user(), password=password, timeout=45)

    code, o, e = ensure_mas_earth2_env(c)
    print("ensure .env exit", code)
    print((o + e).strip())

    print("=== systemd drop-in EARTH2_API_URL ===")
    apply_mas_systemd_earth2_dropin(c, password)

    print("=== git pull + pip install -e . ===")
    pull_cmd = (
        "set -e; MAS_DIR=/home/mycosoft/mycosoft/mas; "
        '[ -d /opt/mycosoft/mas ] && MAS_DIR=/opt/mycosoft/mas; cd "$MAS_DIR" && '
        "git fetch origin && git reset --hard origin/main && "
        "test -x ./venv/bin/pip && ./venv/bin/pip install -e . -q"
    )
    code1, o1, e1 = exec_plain(c, "bash -lc " + shlex.quote(pull_cmd), timeout=900)
    print("exit", code1, (o1 + e1).strip()[-3500:] or "(ok)")

    print("=== systemctl restart mas-orchestrator ===")
    sudo_restart_mas(c, password)

    for attempt in range(36):
        time.sleep(2.5)
        _, live, _ = exec_plain(
            c,
            "curl -sS -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/live",
            timeout=20,
        )
        if live.strip() == "200":
            print("live 200 after ~", (attempt + 1) * 2.5, "s")
            break
    else:
        print("WARN: /live not 200 in time")

    _, st, _ = exec_plain(
        c,
        "curl -sS -m 20 http://127.0.0.1:8001/api/earth2/status",
        timeout=35,
    )
    print("=== GET /api/earth2/status (truncated) ===")
    print(st.strip()[:2000])

    c.close()
    if code1 != 0:
        raise SystemExit(f"MAS git/pip failed exit {code1}")


def safe_sandbox_187() -> None:
    password = pw()
    host = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")
    print("\n=== Sandbox safe prune:", host, "===")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user(), password=password, timeout=45)

    cmds = [
        "echo '--- before ---' && docker system df 2>/dev/null | head -40",
        "docker builder prune -f 2>&1 | tail -20",
        "docker image prune -f 2>&1 | tail -15",
        "echo '--- after ---' && docker system df 2>/dev/null | head -40",
        "free -h | head -5",
    ]
    for cmd in cmds:
        code, o, e = exec_plain(c, cmd, timeout=600)
        print("\n$", cmd[:80], "... exit", code)
        blob = (o + e).strip()
        print(blob[-4000:] if len(blob) > 4000 else blob)

    c.close()


def try_legion_ssh(
    host: str,
    users: list[str],
    password: str,
    probe: str,
) -> None:
    print(f"\n=== Legion probe {host} ===")
    for u in users:
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(host, username=u, password=password, timeout=12, allow_agent=False, look_for_keys=False)
            code, o, e = exec_plain(c, probe, timeout=45)
            print(f"user={u} exit={code}")
            print((o + e).strip()[:1500])
            c.close()
            return
        except Exception as ex:
            print(f"user={u} failed: {ex}")


def main() -> None:
    load_creds()
    deploy_mas_188()
    safe_sandbox_187()

    # Same password often works for local Windows accounts (best-effort).
    p = pw()
    try_legion_ssh(
        os.environ.get("GPU_VOICE_IP", "192.168.0.241"),
        [os.environ.get("LEGION_VOICE_USER", "owner1"), "mycosoft", "Administrator"],
        p,
        'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8998,8999,11434 -ErrorAction SilentlyContinue | Select-Object LocalPort,State | Format-Table"',
    )
    try_legion_ssh(
        os.environ.get("GPU_EARTH2_IP", "192.168.0.249"),
        [os.environ.get("LEGION_EARTH2_USER", "owner2"), "owner1", "mycosoft"],
        p,
        'powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8220/health -TimeoutSec 5).Content } catch { $_.Exception.Message }"',
    )

    print(
        "\nDone. If Legions failed SSH or need firewall rules, run elevated on each host:\n"
        "  scripts/gpu-node/windows/Ensure-VoiceLANFirewall.ps1\n"
        "  scripts/gpu-node/windows/Ensure-Earth2LANFirewall.ps1\n"
    )


if __name__ == "__main__":
    main()
