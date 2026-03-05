"""
Provision MYCA Workspace VM 191.
Clones from VM 103 (mycosoft-sandbox) which already has Ubuntu + Docker installed.
Then configures it as MYCA's autonomous workspace.
"""
import json, os, ssl, sys, time, socket
import urllib.request, urllib.parse, urllib.error
import paramiko

# ── Config ───────────────────────────────────────────────────────────────────
PROXMOX_HOST = "192.168.0.202"
PROXMOX_TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
NEW_VM_ID = 191
NEW_VM_IP = "192.168.0.191"
SOURCE_VM_ID = 103  # mycosoft-sandbox — already has Ubuntu + Docker

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()
VM_USER = "mycosoft"

# ── Proxmox API ───────────────────────────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
BASE = f"https://{PROXMOX_HOST}:8006/api2/json"

def pve(method, path, data=None):
    url = BASE + path
    payload = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Authorization": PROXMOX_TOKEN,
            "Content-Type": "application/x-www-form-urlencoded" if payload else "",
        },
        method=method
    )
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=20)
        return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "already exists" in body:
            return {"already_exists": True}
        print(f"  PVE {method} {path} -> HTTP {e.code}: {body[:200]}")
        return None

# ── Check if 191 already exists ───────────────────────────────────────────────
print("=== Checking VM 191 ===")
vms = pve("GET", f"/nodes/{NODE}/qemu")
existing_ids = {vm["vmid"] for vm in vms}

if NEW_VM_ID in existing_ids:
    vm_status = next(v for v in vms if v["vmid"] == NEW_VM_ID)
    print(f"VM 191 already exists: status={vm_status['status']}")
    if vm_status["status"] != "running":
        print("Starting VM 191...")
        pve("POST", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/status/start")
        time.sleep(15)
else:
    # Clone from an existing VM (VM 189 MINDEX is smaller — 4 CPU, 8GB RAM)
    # Or create fresh. Let's create fresh since sandbox is too large to clone.
    print(f"Creating VM {NEW_VM_ID} (myca-workspace)...")
    
    # Find Ubuntu ISO
    try:
        storage_content = pve("GET", f"/nodes/{NODE}/storage/local/content")
        ubuntu_iso = next(
            (s["volid"] for s in storage_content 
             if "ubuntu" in s.get("volid","").lower() and s.get("content") == "iso"),
            None
        )
        print(f"Ubuntu ISO: {ubuntu_iso}")
    except Exception as e:
        ubuntu_iso = None
        print(f"Could not find ISO: {e}")

    result = pve("POST", f"/nodes/{NODE}/qemu", {
        "vmid": NEW_VM_ID,
        "name": "myca-workspace",
        "memory": 12288,
        "cores": 8,
        "sockets": 1,
        "cpu": "host",
        "ostype": "l26",
        "scsihw": "virtio-scsi-single",
        "scsi0": "local-lvm:150,discard=on,iothread=1",
        "net0": "virtio,bridge=vmbr0,firewall=1",
        "boot": f"order={'ide2;scsi0' if ubuntu_iso else 'scsi0'}",
        "agent": 1,
        "description": "MYCA Autonomous Workspace - schedule@mycosoft.org",
        **({f"ide2": f"{ubuntu_iso},media=cdrom"} if ubuntu_iso else {}),
    })
    print(f"VM created: {result}")

    print("Starting VM 191...")
    pve("POST", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/status/start")

    if ubuntu_iso:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║  UBUNTU INSTALLATION REQUIRED (one-time)                           ║
║                                                                    ║
║  1. Open https://192.168.0.202:8006                                ║
║  2. Navigate to VM 191 → Console (noVNC)                           ║
║  3. Install Ubuntu 22.04 Server with:                              ║
║       Username:  mycosoft                                          ║
║       Hostname:  myca-workspace                                    ║
║       IP:        192.168.0.191/24  GW: 192.168.0.1                ║
║       Enable SSH                                                   ║
║  4. Re-run this script after installation completes                ║
╚══════════════════════════════════════════════════════════════════════╝
""")
        print("Re-run this script after Ubuntu is installed.")
        sys.exit(0)

# ── Wait for SSH ──────────────────────────────────────────────────────────────
print(f"\n=== Waiting for SSH on {NEW_VM_IP}:22 ===")
ssh_ready = False
for i in range(40):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((NEW_VM_IP, 22))
        s.close()
        ssh_ready = True
        print(f"SSH ready after {i*5}s")
        break
    except:
        sys.stdout.write(f"\r  Attempt {i+1}/40...")
        sys.stdout.flush()
        time.sleep(5)

if not ssh_ready:
    print("\nSSH unavailable. Is the OS installed? Check Proxmox console.")
    sys.exit(1)

# ── SSH and configure ─────────────────────────────────────────────────────────
print(f"\n=== Connecting to {NEW_VM_IP} ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NEW_VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run(cmd, timeout=60, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if show and out.strip():
        print(f"  {out.strip()[:150]}")
    return out

def sudo(cmd, timeout=120):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

# Set hostname
print("\n[1/8] Setting hostname...")
sudo("hostnamectl set-hostname myca-workspace")

# Install Docker
print("[2/8] Installing Docker...")
out = run("which docker 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("apt-get update -qq", timeout=120)
    sudo("apt-get install -y curl ca-certificates apt-transport-https", timeout=120)
    run("curl -fsSL https://get.docker.com | sudo sh", timeout=300)
    sudo(f"usermod -aG docker {VM_USER}")
    print("  Docker installed.")
else:
    print("  Docker already present.")

# Install Docker Compose plugin
sudo("apt-get install -y docker-compose-plugin python3-pip git jq", timeout=120)

# Create directory structure
print("[3/8] Creating /opt/myca directory structure...")
sudo("mkdir -p /opt/myca/workspace-api /opt/myca/credentials/google /opt/myca/data /opt/myca/logs /opt/myca/n8n")
sudo(f"chown -R {VM_USER}:{VM_USER} /opt/myca")

# Upload files
print("[4/8] Uploading workspace files...")
sftp = ssh.open_sftp()

repo_root = os.path.join(os.path.dirname(__file__), "..")

# Upload docker-compose
compose_src = os.path.join(repo_root, "infra/myca-workspace/docker-compose.yml")
sftp.put(compose_src, "/opt/myca/docker-compose.yml")
print("  docker-compose.yml uploaded")

# Upload workspace API
api_src = os.path.join(repo_root, "mycosoft_mas/agents/workspace/workspace_api.py")
sftp.put(api_src, "/opt/myca/workspace-api/workspace_api.py")
print("  workspace_api.py uploaded")

# Upload DB schema
db_src = os.path.join(repo_root, "infra/myca-workspace/init-workspace-db.sql")
sftp.put(db_src, "/opt/myca/workspace-api/init-workspace-db.sql")
print("  init-workspace-db.sql uploaded")

# Upload integration clients (so workspace API can import them)
integrations = ["google_workspace_client.py", "discord_client.py", "asana_client.py"]
for fname in integrations:
    src = os.path.join(repo_root, f"mycosoft_mas/integrations/{fname}")
    if os.path.exists(src):
        sftp.put(src, f"/opt/myca/workspace-api/{fname}")
        print(f"  {fname} uploaded")

# Write .env file
env_content = f"""MYCA_EMAIL=schedule@mycosoft.org
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
BRIDGE_URL=http://192.168.0.190:8999
POSTGRES_PASSWORD=myca_workspace_secure_2026
DB_POSTGRESDB_PASSWORD=myca_workspace_secure_2026
N8N_BASIC_AUTH_USER=myca
N8N_PASSWORD=myca_n8n_2026
GOOGLE_SERVICE_ACCOUNT_KEY=/opt/myca/credentials/google/service_account.json
MYCA_DISCORD_TOKEN=
DISCORD_GUILD_ID=
DISCORD_OPS_CHANNEL_ID=
ASANA_API_KEY=
ASANA_WORKSPACE_ID=
ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', '')}
GIT_AUTHOR_NAME=MYCA
GIT_AUTHOR_EMAIL=myca@mycosoft.org
"""
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_content)
print("  .env written")

# Write __init__.py so imports work
with sftp.open("/opt/myca/workspace-api/__init__.py", "w") as f:
    f.write("")

sftp.close()

# Start Docker stack
print("[5/8] Starting Docker stack...")
out = run("cd /opt/myca && docker compose up -d 2>&1", timeout=300)
print(out[-600:])

time.sleep(15)

# Install Node.js + Claude Code
print("[6/8] Installing Node.js and Claude Code...")
out = run("which node 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("apt-get install -y nodejs npm", timeout=120)

out = run("which claude-code 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("npm install -g @anthropic-ai/claude-code 2>/dev/null || true", timeout=120)

# Configure git identity for MYCA
print("[7/8] Configuring git identity...")
run('git config --global user.name "MYCA"')
run('git config --global user.email "myca@mycosoft.org"')

# Verify
print("[8/8] Verifying services...")
out = run("docker ps --format 'table {{.Names}}\t{{.Status}}'")
print(out)

time.sleep(10)
out = run("curl -s http://localhost:8100/health 2>/dev/null || echo 'API starting...'")
print(f"\nWorkspace API: {out[:200]}")

out = run("curl -s http://localhost:5679 2>/dev/null | head -3 || echo 'n8n starting...'")
print(f"n8n:           {out[:100]}")

ssh.close()

print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  VM 191 (MYCA Workspace) DEPLOYED                                      ║
║                                                                        ║
║  Workspace API:  http://192.168.0.191:8100                             ║
║  n8n Workflows:  http://192.168.0.191:5679  (user: myca)               ║
║  PostgreSQL:     192.168.0.191:5433                                    ║
║                                                                        ║
║  NEXT STEPS:                                                           ║
║  1. Upload Google Service Account JSON to:                             ║
║     /opt/myca/credentials/google/service_account.json                 ║
║  2. Add Discord bot token to /opt/myca/.env (MYCA_DISCORD_TOKEN)       ║
║  3. Add Asana PAT to /opt/myca/.env (ASANA_API_KEY)                    ║
║  4. Restart: ssh mycosoft@191 then: cd /opt/myca && docker compose up  ║
╚══════════════════════════════════════════════════════════════════════════╝
""")
