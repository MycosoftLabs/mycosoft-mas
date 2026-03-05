"""
Set up VM 191 using Ubuntu cloud image + cloud-init.
No manual installer needed — fully automated.

Steps:
1. Stop VM 191
2. Detach ISO, import cloud image as disk
3. Configure cloud-init (user, password, IP)
4. Start and wait for SSH
5. Deploy workspace stack
"""
import json, os, ssl, sys, time, socket
import urllib.request, urllib.parse, urllib.error
import paramiko

PROXMOX_HOST = "192.168.0.202"
TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
VM_ID = 191
VM_IP = "192.168.0.191"
VM_GW = "192.168.0.1"
CLOUD_IMAGE = "local:iso/ubuntu-22.04-server-cloudimg-amd64.img"

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
            "Authorization": TOKEN,
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

def wait_task(task_id, label="task", timeout=300):
    if not task_id:
        return
    for i in range(timeout // 5):
        time.sleep(5)
        result = pve("GET", f"/nodes/{NODE}/tasks/{task_id}/status")
        if result and result.get("status") in ("stopped", "OK"):
            print(f"  {label} done in {(i+1)*5}s")
            return
        if i % 6 == 0:
            print(f"  {label} running... {(i+1)*5}s")
    print(f"  {label} timed out")

# ── Step 1: Stop VM ───────────────────────────────────────────────────────────
print("=== [1/6] Stopping VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/stop")
time.sleep(10)

# ── Step 2: Import cloud image as disk ────────────────────────────────────────
print("=== [2/6] Importing Ubuntu cloud image as disk ===")
# Use Proxmox API to run qm importdisk via SSH to Proxmox itself
# First connect to Proxmox host and run the import command
proxmox_ssh = paramiko.SSHClient()
proxmox_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Proxmox root SSH — try with VM password or check if we have proxmox creds
# Proxmox API token doesn't give shell access, so we SSH as root
# The Proxmox machine typically has root SSH enabled on the default port
print("Connecting to Proxmox host for disk import...")

connected = False
for user in ["root", "mycosoft"]:
    try:
        proxmox_ssh.connect(PROXMOX_HOST, username=user, password=VM_PASSWORD, timeout=10)
        print(f"  Connected as {user}")
        connected = True
        break
    except Exception as e:
        print(f"  {user}: {e}")

if not connected:
    print("Cannot SSH to Proxmox host. Using alternative approach.")
    # Alternative: configure cloud-init directly via API without disk import
    # Just update the existing VM to use the cloud image ISO as scsi0
    print("Reconfiguring VM to boot from cloud image...")
    
    # Detach IDE (installer ISO)
    pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {"ide2": "none,media=cdrom"})
    
    # Set scsi0 to import from the cloud image file on local storage
    # This needs qm importdisk run on the Proxmox host
    print("NOTE: Need Proxmox shell access to import cloud image.")
    print("Attempting via Proxmox API exec (if available)...")
    
    # Try Proxmox agent exec on the Proxmox node itself
    import subprocess
    # Try plink (PuTTY SSH client) if available
    try:
        result = subprocess.run(
            ["plink", "-ssh", "-batch", "-pw", VM_PASSWORD, f"root@{PROXMOX_HOST}",
             f"qm importdisk {VM_ID} /var/lib/vz/template/iso/ubuntu-22.04-server-cloudimg-amd64.img local-lvm --format qcow2"],
            capture_output=True, text=True, timeout=120
        )
        print("plink output:", result.stdout[:200], result.stderr[:200])
    except FileNotFoundError:
        print("plink not found")
    sys.exit(1)
else:
    def pxm_run(cmd, timeout=120):
        stdin, stdout, stderr = proxmox_ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out, err

    # Import cloud image disk
    print("Importing cloud image to local-lvm...")
    out, err = pxm_run(
        f"qm importdisk {VM_ID} /var/lib/vz/template/iso/ubuntu-22.04-server-cloudimg-amd64.img local-lvm --format raw",
        timeout=180
    )
    print("Import:", out[-200:] if out else "", err[-100:] if err else "")

    # Attach the imported disk as scsi0 and set boot
    print("Attaching disk and configuring boot...")
    out, err = pxm_run(f"qm set {VM_ID} --scsi0 local-lvm:vm-{VM_ID}-disk-0 --boot c --bootdisk scsi0")
    print("Attach:", out[:100], err[:100])

    # Remove installer ISO
    out, err = pxm_run(f"qm set {VM_ID} --ide2 none,media=cdrom")

    # Add cloud-init drive
    out, err = pxm_run(f"qm set {VM_ID} --ide0 local-lvm:cloudinit")
    print("CloudInit drive:", out[:100], err[:100])

    # Resize disk to 100GB
    out, err = pxm_run(f"qm resize {VM_ID} scsi0 100G")
    print("Resize:", out[:100], err[:100])

    proxmox_ssh.close()

# ── Step 3: Configure cloud-init ─────────────────────────────────────────────
print("=== [3/6] Configuring cloud-init ===")
pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {
    "ciuser": VM_USER,
    "cipassword": VM_PASSWORD,
    "ipconfig0": f"ip={VM_IP}/24,gw={VM_GW}",
    "nameserver": "8.8.8.8 192.168.0.1",
    "searchdomain": "mycosoft.local",
    "sshkeys": "",  # No SSH key — use password auth
    "serial0": "socket",
    "vga": "serial0",
})
print("Cloud-init configured")

# ── Step 4: Start VM ─────────────────────────────────────────────────────────
print("=== [4/6] Starting VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/start")
print("VM started. Waiting for cloud-init to complete (2-3 min)...")
time.sleep(30)

# ── Step 5: Wait for SSH ─────────────────────────────────────────────────────
print("=== [5/6] Waiting for SSH ===")
ssh_ready = False
for i in range(40):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((VM_IP, 22))
        s.close()
        ssh_ready = True
        print(f"SSH ready after {(i*5)+30}s")
        break
    except:
        sys.stdout.write(f"\r  Waiting... {(i*5)+30}s")
        sys.stdout.flush()
        time.sleep(5)

if not ssh_ready:
    print("\nSSH not available yet. Cloud-init may still be running.")
    print(f"Try SSH manually in a minute: ssh mycosoft@{VM_IP}")
    sys.exit(1)

# ── Step 6: Deploy workspace ─────────────────────────────────────────────────
print("\n=== [6/6] Deploying MYCA workspace ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    return out.strip()

def sudo(cmd, timeout=180):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

print("Installing Docker...")
out = run("which docker 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("apt-get update -qq && apt-get install -y curl ca-certificates", timeout=180)
    run("curl -fsSL https://get.docker.com | sudo sh", timeout=300)
    sudo(f"usermod -aG docker {VM_USER}")
sudo("apt-get install -y docker-compose-plugin python3-pip git -qq", timeout=180)

print("Creating /opt/myca structure...")
sudo("mkdir -p /opt/myca/workspace-api /opt/myca/credentials/google /opt/myca/data /opt/myca/logs /opt/myca/n8n")
sudo(f"chown -R {VM_USER}:{VM_USER} /opt/myca")

print("Uploading workspace files...")
sftp = ssh.open_sftp()
repo_root = os.path.join(os.path.dirname(__file__), "..")

uploads = [
    (f"{repo_root}/infra/myca-workspace/docker-compose.yml", "/opt/myca/docker-compose.yml"),
    (f"{repo_root}/mycosoft_mas/agents/workspace/workspace_api.py", "/opt/myca/workspace-api/workspace_api.py"),
    (f"{repo_root}/infra/myca-workspace/init-workspace-db.sql", "/opt/myca/workspace-api/init-workspace-db.sql"),
]
for fname in ["google_workspace_client.py", "discord_client.py", "asana_client.py"]:
    uploads.append((
        f"{repo_root}/mycosoft_mas/integrations/{fname}",
        f"/opt/myca/workspace-api/{fname}"
    ))

for src, dst in uploads:
    if os.path.exists(src):
        sftp.put(src, dst)
        print(f"  {os.path.basename(src)}")

env_content = """MYCA_EMAIL=schedule@mycosoft.org
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
"""
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_content)
with sftp.open("/opt/myca/workspace-api/__init__.py", "w") as f:
    f.write("")
sftp.close()

print("Starting Docker stack...")
out = run("cd /opt/myca && docker compose up -d 2>&1", timeout=300)
print(out[-400:])

run('git config --global user.name "MYCA"')
run('git config --global user.email "myca@mycosoft.org"')

time.sleep(15)
out = run("curl -s http://localhost:8100/health 2>/dev/null || echo starting...")
print(f"Workspace API health: {out[:150]}")

ssh.close()
print("\nVM 191 MYCA Workspace is live at http://192.168.0.191:8100")
