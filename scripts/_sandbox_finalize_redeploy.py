#!/usr/bin/env python3
"""Finalize Sandbox website redeploy after tunnel/DNS recovery."""
from __future__ import annotations

import os
import time
from pathlib import Path

import paramiko


def load_password() -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in {"VM_PASSWORD", "VM_SSH_PASSWORD"} and v.strip():
                pw = v.strip()
                break
    return pw


def run_stream(ssh: paramiko.SSHClient, cmd: str, timeout: int = 2400) -> int:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
    del stdin
    channel = stdout.channel
    start = time.time()
    while True:
        if channel.recv_ready():
            data = channel.recv(4096).decode("utf-8", errors="replace")
            if data:
                print(data, end="")
        if channel.recv_stderr_ready():
            data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
            if data:
                print(data, end="")
        if channel.exit_status_ready():
            # flush any remaining buffered output
            while channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                if data:
                    print(data, end="")
            while channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                if data:
                    print(data, end="")
            return channel.recv_exit_status()
        if time.time() - start > timeout:
            raise TimeoutError(f"Timed out after {timeout}s: {cmd}")
        time.sleep(0.2)


def main() -> int:
    pw = load_password()
    if not pw:
        print("ERROR: missing VM password")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=20)
    try:
        steps = [
            (
                "Convert non-UTF8 files to UTF-8",
                r"""python3 - <<'PY'
from pathlib import Path
root=Path('/home/mycosoft/mycosoft/website')
converted=[]
for p in root.rglob('*'):
    if not p.is_file():
        continue
    if p.suffix.lower() not in {'.ts','.tsx','.js','.jsx','.json','.md','.css','.yml','.yaml'}:
        continue
    b=p.read_bytes()
    try:
        b.decode('utf-8')
        continue
    except Exception:
        pass
    txt=None
    for enc in ('utf-16','utf-16le','utf-16be','cp1252','latin-1'):
        try:
            txt=b.decode(enc)
            break
        except Exception:
            pass
    if txt is None:
        continue
    p.write_text(txt,encoding='utf-8')
    converted.append(str(p))
print('converted_count',len(converted))
for f in converted:
    print(f)
PY""",
            ),
            (
                "Patch broken ancestry import",
                r"""python3 - <<'PY'
from pathlib import Path
p=Path('/home/mycosoft/mycosoft/website/app/ancestry/layout.tsx')
text=p.read_text(encoding='utf-8',errors='replace')
text='\n'.join([ln for ln in text.splitlines() if 'navigation-title' not in ln])
text=text.replace('<NavigationTitle />','<h2 className="text-sm font-semibold text-gray-200">Navigation</h2>')
text=text.replace('<h2 className=" text-sm font-semibold text-gray-200>Navigation</h2>','<h2 className="text-sm font-semibold text-gray-200">Navigation</h2>')
p.write_text(text+'\n',encoding='utf-8')
print('patched',p)
PY""",
            ),
            (
                "Build and run website container",
                r"""
cd /home/mycosoft/mycosoft/website && \
docker stop mycosoft-website >/dev/null 2>&1 || true && \
docker rm mycosoft-website >/dev/null 2>&1 || true && \
DOCKER_BUILDKIT=0 docker build -f Dockerfile.production -t mycosoft-always-on-mycosoft-website:latest --no-cache . && \
docker run -d --name mycosoft-website -p 3000:3000 -v /opt/mycosoft/media/website/assets:/app/public/assets:ro --restart unless-stopped mycosoft-always-on-mycosoft-website:latest && \
docker ps --filter name=mycosoft-website --format '{{.Names}} {{.Status}}'
""",
            ),
            (
                "Verify tunnel and website health",
                "systemctl is-active cloudflared && curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/",
            ),
        ]

        for title, cmd in steps:
            print(f"\n=== {title} ===")
            code = run_stream(ssh, cmd, timeout=3000)
            print(f"\n(exit={code})")
            if code != 0:
                return code
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
