"""
Fast VM 191 provisioning: clone from VM 189 (MINDEX-VM, already has Ubuntu+Docker),
then reconfigure as MYCA's workspace.
"""
import json, os, ssl, sys, time, socket
import urllib.request, urllib.parse, urllib.error
import paramiko

PROXMOX_HOST = "192.168.0.202"
PROXMOX_TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
SOURCE_VM_ID = 189   # MINDEX-VM: Ubuntu + Docker already installed
NEW_VM_ID = 191
NEW_VM_IP = "192.168.0.191"
SOURCE_VM_IP = "192.168.0.189"

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()
VM_USER = "mycosoft"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
BASE = f"https://{PROXMOX_HOST}:8006/api2/json"

def pve(method, path, data=None):
    payload = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(
        BASE + path, data=payload,
        headers={
            "Authorization": PROXMOX_TOKEN,
            "Content-Type": "application/x-www-form-urlencoded" if payload else "",
        },
        method=method
    )
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:200]}")
        return None

# Check if 191 already exists
vms = pve("GET", f"/nodes/{NODE}/qemu")
vm_map = {v["vmid"]: v for v in vms}

if NEW_VM_ID in vm_map:
    status = vm_map[NEW_VM_ID]["status"]
    print(f"VM 191 exists (status={status})")
    if status != "running":
        # Delete old failed VM and re-clone
        print("Stopping and deleting old VM 191 to re-clone...")
        pve("POST", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/status/stop")
        time.sleep(5)
        pve("DELETE", f"/nodes/{NODE}/qemu/{NEW_VM_ID}?purge=1")
        time.sleep(5)
        vm_map.pop(NEW_VM_ID, None)
    else:
        print("VM 191 is running - checking SSH...")
        try:
            s = socket.socket()
            s.settimeout(3)
            s.connect((NEW_VM_IP, 22))
            s.close()
            print("SSH already available on 191 - skipping creation")
            # Jump to configure
            goto_configure = True
        except:
            print("Running but SSH not available - something wrong")
            goto_configure = False
else:
    goto_configure = False

if NEW_VM_ID not in vm_map:
    # Clone from VM 189
    print(f"Cloning VM {SOURCE_VM_ID} -> VM {NEW_VM_ID} (myca-workspace)...")
    print("This takes 2-5 minutes for a full clone...")
    result = pve("POST", f"/nodes/{NODE}/qemu/{SOURCE_VM_ID}/clone", {
        "newid": NEW_VM_ID,
        "name": "myca-workspace",
        "full": 1,
        "description": "MYCA Autonomous Workspace - schedule@mycosoft.org",
        "storage": "local-lvm",
    })
    print(f"Clone task: {result}")
    
    # Wait for clone to complete (poll task)
    print("Waiting for clone to complete...")
    for i in range(60):
        time.sleep(10)
        tasks = pve("GET", f"/nodes/{NODE}/tasks")
        recent = [t for t in (tasks or []) if str(NEW_VM_ID) in str(t.get("id","")) or "clone" in str(t.get("type","")).lower()]
        done_tasks = [t for t in recent if t.get("status") in ("stopped", "OK")]
        if done_tasks:
            print(f"Clone completed after {(i+1)*10}s")
            break
        if i % 3 == 0:
            print(f"  Still cloning... ({(i+1)*10}s)")
    
    # Resize disk from 8GB to 100GB
    print("Resizing disk to 100GB...")
    pve("PUT", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/resize", {
        "disk": "scsi0",
        "size": "+92G",  # Add 92GB to existing 8GB = 100GB
    })
    
    # Update VM config: 8 CPUs, 12GB RAM
    print("Updating VM resources (8 CPU, 12GB RAM)...")
    pve("PUT", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/config", {
        "cores": 8,
        "memory": 12288,
        "name": "myca-workspace",
        "description": "MYCA Autonomous Workspace - schedule@mycosoft.org",
    })
    
    # Start VM
    print("Starting VM 191...")
    pve("POST", f"/nodes/{NODE}/qemu/{NEW_VM_ID}/status/start")
    time.sleep(20)

# ── Wait for SSH ──────────────────────────────────────────────────────────────
print(f"\nWaiting for SSH on {NEW_VM_IP}:22...")
ssh_ready = False
for i in range(30):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((NEW_VM_IP, 22))
        s.close()
        ssh_ready = True
        print(f"SSH ready after {i*5}s")
        break
    except:
        sys.stdout.write(f"\r  {i*5}s...")
        sys.stdout.flush()
        time.sleep(5)

if not ssh_ready:
    print("\nSSH timeout. VM may still be booting.")
    print("The VM has been cloned from VM 189. Try again in 2 minutes:")
    print("  python scripts/_clone_vm191.py")
    sys.exit(1)

# ── Configure VM 191 ─────────────────────────────────────────────────────────
print(f"\n=== Configuring VM 191 as MYCA workspace ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Note: Clone will have same IP as source (189). Connect via source IP first.
# Then change its IP to 191.
try:
    ssh.connect(NEW_VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=15)
    already_191 = True
    print("Connected via 192.168.0.191 (IP already set)")
except:
    # Connect via original 189 IP
    print(f"Connecting via source IP {SOURCE_VM_IP}...")
    ssh.connect(SOURCE_VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=15)
    already_191 = False

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    return out.strip()

def sudo(cmd, timeout=120):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

# Set hostname
print("[1/7] Setting hostname to myca-workspace...")
sudo("hostnamectl set-hostname myca-workspace")

if not already_191:
    # Change static IP from 189 to 191
    print("[2/7] Changing IP from 192.168.0.189 to 192.168.0.191...")
    netplan = """network:
  version: 2
  ethernets:
    ens18:
      addresses:
        - 192.168.0.191/24
      routes:
        - to: default
          via: 192.168.0.1
      nameservers:
        addresses: [192.168.0.1, 8.8.8.8]
"""
    sftp_tmp = ssh.open_sftp()
    with sftp_tmp.open("/tmp/netplan.yaml", "w") as f:
        f.write(netplan)
    sftp_tmp.close()
    sudo("cp /tmp/netplan.yaml /etc/netplan/00-installer-config.yaml")
    sudo("netplan apply")
    print("IP changed to 192.168.0.191 — reconnecting...")
    ssh.close()
    time.sleep(8)
    
    # Reconnect via new IP
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(12):
        try:
            ssh.connect(NEW_VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=10)
            print("Reconnected via 192.168.0.191")
            break
        except:
            time.sleep(5)

# Stop any MINDEX services that may have been cloned
print("[3/7] Stopping MINDEX services (inherited from clone)...")
sudo("docker stop $(docker ps -q) 2>/dev/null || true")
sudo("docker rm $(docker ps -aq) 2>/dev/null || true")

# Create MYCA directories
print("[4/7] Creating /opt/myca directory structure...")
sudo("mkdir -p /opt/myca/workspace-api /opt/myca/credentials/google /opt/myca/data /opt/myca/logs /opt/myca/n8n")
sudo(f"chown -R {VM_USER}:{VM_USER} /opt/myca")

# Upload workspace files
print("[5/7] Uploading workspace files...")
sftp = ssh.open_sftp()
repo_root = os.path.join(os.path.dirname(__file__), "..")

files = [
    (f"{repo_root}/infra/myca-workspace/docker-compose.yml", "/opt/myca/docker-compose.yml"),
    (f"{repo_root}/mycosoft_mas/agents/workspace/workspace_api.py", "/opt/myca/workspace-api/workspace_api.py"),
    (f"{repo_root}/infra/myca-workspace/init-workspace-db.sql", "/opt/myca/workspace-api/init-workspace-db.sql"),
]

for src, dst in files:
    if os.path.exists(src):
        sftp.put(src, dst)
        print(f"  Uploaded {os.path.basename(src)}")

# Upload integration clients
for fname in ["google_workspace_client.py", "discord_client.py", "asana_client.py"]:
    src = f"{repo_root}/mycosoft_mas/integrations/{fname}"
    if os.path.exists(src):
        sftp.put(src, f"/opt/myca/workspace-api/{fname}")
        print(f"  Uploaded {fname}")

# Write .env
env_content = f"""MYCA_EMAIL=schedule@mycosoft.org
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
BRIDGE_URL=http://192.168.0.190:8999
POSTGRES_PASSWORD=myca_workspace_2026
DB_POSTGRESDB_PASSWORD=myca_workspace_2026
N8N_BASIC_AUTH_USER=myca
N8N_PASSWORD=myca_n8n_2026
GOOGLE_SERVICE_ACCOUNT_KEY=/opt/myca/credentials/google/service_account.json
MYCA_DISCORD_TOKEN=
DISCORD_GUILD_ID=
DISCORD_OPS_CHANNEL_ID=
ASANA_API_KEY=
ASANA_WORKSPACE_ID=
GIT_AUTHOR_NAME=MYCA
GIT_AUTHOR_EMAIL=myca@mycosoft.org
"""
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_content)
with sftp.open("/opt/myca/workspace-api/__init__.py", "w") as f:
    f.write("")
sftp.close()

# Start Docker stack
print("[6/7] Starting MYCA workspace Docker stack...")
out = run("cd /opt/myca && docker compose up -d 2>&1", timeout=300)
print(out[-400:] if len(out) > 400 else out)

time.sleep(20)

# Configure git
run('git config --global user.name "MYCA"')
run('git config --global user.email "myca@mycosoft.org"')

# Verify
print("[7/7] Verification...")
out = run("docker ps --format '{{.Names}}\t{{.Status}}'")
print("Containers:\n" + out)

out = run("curl -s http://localhost:8100/health 2>/dev/null || echo 'starting...'")
print(f"Workspace API: {out[:200]}")

ssh.close()

print("""
+----------------------------------------------------------------------+
|  VM 191 MYCA WORKSPACE DEPLOYED                                    |
|                                                                    |
|  Workspace API:   http://192.168.0.191:8100                        |
|  n8n Workflows:   http://192.168.0.191:5679  (user: myca)          |
|  PostgreSQL:      192.168.0.191:5433                               |
|                                                                    |
|  CREDENTIALS NEEDED (add to /opt/myca/.env on VM 191):            |
|  1. MYCA_DISCORD_TOKEN   - MYCA's Discord bot token               |
|  2. ASANA_API_KEY        - MYCA's Asana PAT                        |
|  3. Google SA JSON at /opt/myca/credentials/google/               |
+----------------------------------------------------------------------+
""")
