#!/usr/bin/env python3
"""
Full OpenClaw fix on Jetson 123: diagnose, enable linger, run manually to capture
errors, fix systemd, verify reachability.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.123"
USER = "jetson"
PORT = 18789


def load_password() -> str:
    pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if not pw and creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("JETSON_SSH_PASSWORD", "VM_PASSWORD", "VM_SSH_PASSWORD") and v.strip():
                pw = v.strip()
                break
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 30) -> tuple[str, str, int]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    _ = stdout.channel.recv_exit_status()
    return out, err, stdout.channel.exit_status


def safe_print(s: str) -> None:
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: Set JETSON_SSH_PASSWORD or VM_PASSWORD in .credentials.local")
        return 1

    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=pw, timeout=30)
    except Exception as e:
        print(f"SSH failed: {e}")
        return 1

    try:
        # 1. Stop service so port is free for manual test
        print("\n--- Stopping OpenClaw service ---")
        run(ssh, "systemctl --user stop openclaw-gateway 2>/dev/null; sleep 1; true")

        # 2. Run OpenClaw manually for 8s to capture startup output
        # OpenClaw uses --bind lan (not --host) for 0.0.0.0 / LAN access
        print("\n--- Running OpenClaw manually (8s) to capture output ---")
        out, err, code = run(
            ssh,
            "timeout 8 bash -l -c 'npx --yes openclaw gateway --port 18789 --bind lan --allow-unconfigured 2>&1' || true",
            timeout=15,
        )
        combined = (out or "") + (err or "")
        safe_print(combined if combined else "(no output)")
        if "listen" in combined.lower() or "ready" in combined.lower() or "18789" in combined:
            print("(OpenClaw likely started successfully during manual run)")

        # 3. Check if port was listening during that window (we can't check mid-run easily, so check now)
        out, _, _ = run(ssh, "ss -tlnp 2>/dev/null | grep 18789 || echo '(none)'")
        safe_print(out.strip() or "(port not in use now)")

        # 4. Enable linger so user services run without active login
        print("\n--- Enabling linger for jetson user ---")
        _stdin, stdout, stderr = ssh.exec_command(
            "sudo -S loginctl enable-linger jetson 2>&1", get_pty=True
        )
        _stdin.write(pw + "\n")
        _stdin.channel.shutdown_write()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        safe_print(out or err or "(done)")

        # 5. Ensure service file has absolute path and logging
        svc_path = "/home/jetson/.config/systemd/user/openclaw-gateway.service"
        log_path = "/home/jetson/.local/state/openclaw-gateway.log"
        run(ssh, "mkdir -p /home/jetson/.local/state")

        # Get npx path
        out, _, _ = run(ssh, "which npx 2>/dev/null || echo /usr/bin/npx")
        npx_path = (out or "").strip().splitlines()[-1].strip() or "/usr/bin/npx"

        run(
            ssh,
            f"""cat > {svc_path} << 'SVCEOF'
[Unit]
Description=OpenClaw Gateway - On-Site AI for MycoBrain
After=network.target

[Service]
Type=simple
Environment=PATH=/usr/bin:/bin:/usr/local/bin:/home/jetson/.local/share/npm/bin
Environment=OPENCLAW_PORT=18789
ExecStart={npx_path} --yes openclaw gateway --port 18789 --bind lan --allow-unconfigured
Restart=on-failure
RestartSec=10
StandardOutput=append:{log_path}
StandardError=append:{log_path}

[Install]
WantedBy=default.target
SVCEOF
""",
        )

        out, _, _ = run(ssh, f"cat {svc_path}")
        safe_print("\n--- Service file ---\n" + out)

        # 5b. Configure OpenClaw for non-loopback Control UI (required when --bind lan)
        print("\n--- Configuring OpenClaw Control UI (allowedOrigins / fallback) ---")
        merge_script = """import json
from pathlib import Path
p = Path('/home/jetson/.openclaw/openclaw.json')
p.parent.mkdir(parents=True, exist_ok=True)
cfg = json.loads(p.read_text()) if p.exists() else {}
if 'gateway' not in cfg: cfg['gateway'] = {}
if 'controlUi' not in cfg['gateway']: cfg['gateway']['controlUi'] = {}
cfg['gateway']['controlUi']['dangerouslyAllowHostHeaderOriginFallback'] = True
p.write_text(json.dumps(cfg, indent=2))
"""
        sftp = ssh.open_sftp()
        try:
            sftp.putfo(io.BytesIO(merge_script.encode("utf-8")), "/tmp/merge_openclaw_cfg.py")
        finally:
            sftp.close()
        run(ssh, "python3 /tmp/merge_openclaw_cfg.py")
        out, _, _ = run(ssh, "cat /home/jetson/.openclaw/openclaw.json 2>/dev/null || echo '(no config)'")
        safe_print(out or "(empty)")

        # 6. Reload and start
        print("\n--- Starting OpenClaw service ---")
        run(ssh, "systemctl --user daemon-reload; systemctl --user enable openclaw-gateway; systemctl --user start openclaw-gateway")
        import time
        time.sleep(4)

        out, _, _ = run(ssh, "systemctl --user status openclaw-gateway --no-pager")
        safe_print(out)

        # 7. Check port and HTTP
        print("\n--- Verifying port and HTTP ---")
        out, _, _ = run(ssh, "ss -tlnp 2>/dev/null | grep 18789 || echo '(none)'")
        safe_print(out or "(no listener)")

        out, _, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/ 2>/dev/null || echo 'fail'")
        print(f"HTTP check: {out.strip()}")

        # 8. Show last lines of log
        print("\n--- Last 20 lines of OpenClaw log ---")
        out, _, _ = run(ssh, f"tail -20 {log_path} 2>/dev/null || echo '(no log yet)'")
        safe_print(out or "(empty)")

        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
