"""Deploy and start MYCA services on VM 191."""
import paramiko, os, time, socket
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

def ssh_run(host, cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=pw, timeout=10)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    ssh.close()
    return out, err

def tcp_check(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True
    except:
        return False

# ── Step 0: Verify SSH ──
print("=" * 60)
print("STEP 0: Verify SSH to VM 191")
print("=" * 60)
try:
    out, _ = ssh_run("192.168.0.191", "echo CONNECTED; whoami; hostname; uptime")
    print(out.strip())
    print("  SSH: OK")
except Exception as e:
    print(f"  SSH FAILED: {e}")
    exit(1)

# ── Step 1: Check current state ──
print("\n" + "=" * 60)
print("STEP 1: Current state of VM 191")
print("=" * 60)

out, _ = ssh_run("192.168.0.191", "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null; echo '---'; systemctl is-active myca-os 2>/dev/null || echo 'myca-os: not found'; ss -tlnp 2>/dev/null | head -20")
print(out)

# ── Step 2: Check directories ──
print("=" * 60)
print("STEP 2: Check MYCA directories")
print("=" * 60)

out, _ = ssh_run("192.168.0.191", "ls -la /opt/myca/ 2>/dev/null || echo '/opt/myca not found'; echo '---'; ls -la /home/mycosoft/repos/ 2>/dev/null || echo '/home/mycosoft/repos not found'; echo '---'; ls /home/mycosoft/mycosoft/ 2>/dev/null || echo '/home/mycosoft/mycosoft not found'")
print(out)

# ── Step 3: Clone/update MAS repo ──
print("=" * 60)
print("STEP 3: Clone/update MAS repo on 191")
print("=" * 60)

out, err = ssh_run("192.168.0.191", """
if [ -d /home/mycosoft/repos/mycosoft-mas ]; then
    cd /home/mycosoft/repos/mycosoft-mas && git pull origin main 2>&1 | tail -5
    echo "REPO_UPDATED"
else
    mkdir -p /home/mycosoft/repos
    cd /home/mycosoft/repos && git clone https://github.com/MycosoftLabs/mycosoft-mas.git 2>&1 | tail -5
    echo "REPO_CLONED"
fi
""", timeout=60)
print(out.strip())
if err:
    print(f"  stderr: {err[:300]}")

# ── Step 4: Create /opt/myca structure ──
print("\n" + "=" * 60)
print("STEP 4: Create MYCA workspace directories")
print("=" * 60)

out, err = ssh_run("192.168.0.191", """
sudo mkdir -p /opt/myca/logs /opt/myca/data /opt/myca/config
sudo chown -R mycosoft:mycosoft /opt/myca
echo "Directories created"
ls -la /opt/myca/
""")
print(out.strip())

# ── Step 5: Create .env for MYCA ──
print("\n" + "=" * 60)
print("STEP 5: Create MYCA environment config")
print("=" * 60)

anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
openai_key = os.environ.get("OPENAI_API_KEY", "")

env_content = f"""# MYCA OS Environment
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_REDIS_URL=redis://192.168.0.189:6379
QDRANT_URL=http://192.168.0.189:6333
MINDEX_PG_HOST=192.168.0.189

MYCA_N8N_URL=http://localhost:5679
MYCA_REPOS_DIR=/home/mycosoft/repos

ANTHROPIC_API_KEY={anthropic_key}
OPENAI_API_KEY={openai_key}

MORGAN_EMAIL=morgan@mycosoft.org
"""

# Write env via SSH
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)

sftp = ssh.open_sftp()
with sftp.file("/opt/myca/.env", "w") as f:
    f.write(env_content)
sftp.close()
print("  /opt/myca/.env created")

# ── Step 6: Install Python dependencies ──
print("\n" + "=" * 60)
print("STEP 6: Install Python dependencies")
print("=" * 60)

_, stdout, stderr = ssh.exec_command("pip3 install --user aiohttp httpx paramiko redis 2>&1 | tail -5", timeout=60)
print(stdout.read().decode().strip())

# ── Step 7: Create systemd service for MYCA OS ──
print("\n" + "=" * 60)
print("STEP 7: Create systemd service")
print("=" * 60)

service_content = """[Unit]
Description=MYCA Operating System Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mycosoft
WorkingDirectory=/home/mycosoft/repos/mycosoft-mas
EnvironmentFile=/opt/myca/.env
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
    f.write(service_content)
sftp.close()

_, stdout, stderr = ssh.exec_command("sudo cp /tmp/myca-os.service /etc/systemd/system/myca-os.service && sudo systemctl daemon-reload && echo SERVICE_INSTALLED", timeout=15)
print(stdout.read().decode().strip())
err = stderr.read().decode()
if err:
    print(f"  stderr: {err[:200]}")

# ── Step 8: Start MYCA OS ──
print("\n" + "=" * 60)
print("STEP 8: Start MYCA OS daemon")
print("=" * 60)

_, stdout, stderr = ssh.exec_command("sudo systemctl enable myca-os && sudo systemctl start myca-os && sleep 3 && systemctl is-active myca-os", timeout=20)
out = stdout.read().decode().strip()
err = stderr.read().decode()
print(f"  myca-os status: {out}")
if err:
    print(f"  stderr: {err[:300]}")

# Check logs
_, stdout, _ = ssh.exec_command("tail -20 /opt/myca/logs/myca_os.log 2>/dev/null")
print("\n  Recent logs:")
print(stdout.read().decode()[:1000])

ssh.close()

# ── Step 9: Verify ──
print("\n" + "=" * 60)
print("STEP 9: Final verification")
print("=" * 60)

time.sleep(3)
for port, name in [(22, "SSH"), (8000, "FastAPI"), (5679, "n8n")]:
    ok = tcp_check("192.168.0.191", port)
    print(f"  {name:15s} 191:{port}  {'OPEN' if ok else 'CLOSED'}")

# Check MAS health too
import urllib.request
try:
    with urllib.request.urlopen("http://192.168.0.188:8001/health", timeout=5) as r:
        import json
        data = json.loads(r.read().decode())
        pg = next((c for c in data.get("components", []) if c["name"] == "postgresql"), {})
        print(f"\n  MAS Orchestrator: {data['status']} (PG: {pg.get('status', '?')})")
except Exception as e:
    print(f"  MAS health: {e}")

print("\n" + "=" * 60)
print("DEPLOYMENT COMPLETE")
print("=" * 60)
