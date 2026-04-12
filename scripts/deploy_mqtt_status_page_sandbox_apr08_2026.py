#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import paramiko


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mycosoft MQTT Status</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0a0a0a; color:#e5e5e5; margin:0; padding:24px; }
    .card { max-width: 760px; margin: 0 auto; border:1px solid #2a2a2a; border-radius:12px; padding:20px; background:#111; }
    h1 { margin-top:0; font-size: 28px; }
    .ok { color:#34d399; } .bad { color:#f87171; }
    code { background:#1f1f1f; padding:2px 6px; border-radius:6px; }
    .small { color:#9ca3af; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>MQTT Status</h1>
    <p class="small">Updated: 2026-04-08</p>
    <p>Public endpoint (remote): <code>wss://mqtt.mycosoft.com:443</code></p>
    <p>LAN endpoint (fastest): <code>mqtt://192.168.0.196:1883</code></p>
    <p id="wss">Checking WSS endpoint...</p>
    <p class="small">Note: opening <code>https://mqtt.mycosoft.com/</code> in a browser is expected to fail (broker endpoint, not website HTML).</p>
    <hr />
    <p><strong>Jetson settings</strong></p>
    <ul>
      <li>LAN: <code>mqtt://192.168.0.196:1883</code> user <code>mycobrain</code></li>
      <li>Remote: <code>wss://mqtt.mycosoft.com:443</code> path <code>/</code> user <code>mycobrain</code></li>
    </ul>
  </div>
  <script>
    (async function() {
      const el = document.getElementById('wss');
      try {
        const ws = new WebSocket('wss://mqtt.mycosoft.com:443');
        const timer = setTimeout(() => { ws.close(); el.innerHTML = '<span class="ok">WSS endpoint reachable (handshake initiated).</span>'; }, 2500);
        ws.onerror = () => { clearTimeout(timer); el.innerHTML = '<span class="bad">WSS endpoint check returned an error (may still require MQTT auth).</span>'; };
        ws.onopen = () => { clearTimeout(timer); ws.close(); el.innerHTML = '<span class="ok">WSS endpoint reachable.</span>'; };
      } catch (_e) {
        el.innerHTML = '<span class="bad">WSS endpoint check failed.</span>';
      }
    })();
  </script>
</body>
</html>
"""


def load_creds() -> None:
    repo = Path(__file__).resolve().parent.parent
    for p in (
        repo / ".credentials.local",
        repo.parent.parent / "WEBSITE" / "website" / ".credentials.local",
    ):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() and k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip().strip("\"'")


def main() -> int:
    load_creds()
    host = os.environ.get("SANDBOX_VM_HOST") or os.environ.get("SANDBOX_VM_IP") or "192.168.0.187"
    user = os.environ.get("SANDBOX_VM_USER") or os.environ.get("VM_SSH_USER") or "mycosoft"
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        print("ERROR: missing VM_PASSWORD/VM_SSH_PASSWORD")
        return 1

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as f:
        f.write(HTML)
        local_file = f.name

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=20)

    ssh.exec_command("mkdir -p /opt/mycosoft/mqtt-status", timeout=30)
    sftp = ssh.open_sftp()
    try:
        sftp.put(local_file, "/opt/mycosoft/mqtt-status/index.html")
    finally:
        sftp.close()

    cmd = (
        "docker rm -f mqtt-status-page 2>/dev/null || true; "
        "docker run -d --name mqtt-status-page -p 3055:80 "
        "-v /opt/mycosoft/mqtt-status/index.html:/usr/share/nginx/html/index.html:ro "
        "--restart unless-stopped nginx:alpine; "
        "curl -s -o /dev/null -w '%{http_code}' http://localhost:3055"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    ssh.close()
    print(f"HTTP3055={out}")
    if err:
        print(err)
    return 0 if out == "200" else 1


if __name__ == "__main__":
    raise SystemExit(main())
