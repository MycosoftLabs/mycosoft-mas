"""Install MYCA OS Python dependencies on VM 191 and fix the service."""
import paramiko, os, time
from pathlib import Path

def load_creds():
    cf = Path(__file__).parent.parent / ".credentials.local"
    if cf.exists():
        for line in cf.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_creds()
pw = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD", ""))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)

def run(cmd, timeout=60):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

def sudo_run(cmd, timeout=30):
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.get_pty()
    chan.exec_command(f"sudo -S bash -c '{cmd}'")
    chan.send(pw + "\n")
    time.sleep(2)
    out = b""
    try:
        while True:
            chunk = chan.recv(4096)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    chan.close()
    return out.decode(errors="replace")

# 1. Install Python dependencies
print("=== Installing Python dependencies ===")
out, err = run(
    "cd /home/mycosoft/repos/mycosoft-mas && "
    "pip3 install --user fastapi uvicorn httpx aiohttp redis pydantic 2>&1 | tail -10",
    timeout=120,
)
print(out.strip())
if "error" in err.lower():
    print(f"STDERR: {err[:300]}")

# 2. Verify fastapi imports
print("\n=== Verifying imports ===")
out, _ = run("python3 -c 'import fastapi; import httpx; import aiohttp; import redis; print(\"ALL IMPORTS OK\")'")
print(out.strip())

# 3. Fix the systemd service to use system python3 (not .venv)
print("\n=== Fixing systemd service ExecStart ===")
service = """[Unit]
Description=MYCA Operating System Daemon
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=mycosoft
WorkingDirectory=/home/mycosoft/repos/mycosoft-mas
EnvironmentFile=/opt/myca/.env
Environment=PYTHONPATH=/home/mycosoft/repos/mycosoft-mas
Environment=PATH=/home/mycosoft/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 -m mycosoft_mas.myca.os
Restart=on-failure
RestartSec=10
StandardOutput=append:/opt/myca/logs/myca_os.log
StandardError=append:/opt/myca/logs/myca_os_error.log

[Install]
WantedBy=multi-user.target
"""

sftp = ssh.open_sftp()
with sftp.file("/tmp/myca-os.service", "w") as f:
    f.write(service)
sftp.close()

result = sudo_run("cp /tmp/myca-os.service /etc/systemd/system/myca-os.service && systemctl daemon-reload && echo DONE")
print(f"  Service updated: {'DONE' in result}")

# 4. Test manual run
print("\n=== Manual test (3 sec) ===")
out, err = run(
    "cd /home/mycosoft/repos/mycosoft-mas && "
    "PYTHONPATH=/home/mycosoft/repos/mycosoft-mas "
    "timeout 3 python3 -m mycosoft_mas.myca.os 2>&1 | head -20",
    timeout=15,
)
print(out[:800])
if err:
    print(f"STDERR: {err[:300]}")

# 5. Start the service
print("\n=== Starting myca-os service ===")
result = sudo_run("systemctl restart myca-os && sleep 5 && systemctl is-active myca-os")
# Filter out password echo
lines = [l for l in result.splitlines() if pw not in l and not l.startswith("[sudo]")]
print("\n".join(lines[-5:]))

# 6. Check final state
time.sleep(3)
print("\n=== Final status ===")
out, _ = run("systemctl is-active myca-os 2>/dev/null")
print(f"  myca-os: {out.strip()}")

out, _ = run("tail -10 /opt/myca/logs/myca_os.log 2>/dev/null")
if out.strip():
    print("  Recent log:")
    for line in out.strip().splitlines()[-5:]:
        print(f"    {line}")

out, _ = run("tail -5 /opt/myca/logs/myca_os_error.log 2>/dev/null")
if out.strip():
    print("  Error log:")
    print(f"    {out.strip()[:300]}")

ssh.close()
print("\nDone.")
