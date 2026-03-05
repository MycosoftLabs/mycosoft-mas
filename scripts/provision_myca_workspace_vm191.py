"""
Provision VM 191 — MYCA's autonomous workspace.

Creates the VM on Proxmox, waits for it to boot, then SSHes in
to deploy the full workspace Docker stack.
"""
import json
import os
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse
import subprocess
import sys

# ── Proxmox config ──────────────────────────────────────────────────────────
PROXMOX_HOST = "192.168.0.202"
PROXMOX_TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
VM_ID = 191
VM_NAME = "myca-workspace"
VM_IP = "192.168.0.191"
VM_CPU = 8
VM_RAM = 12288   # 12 GB
VM_DISK = "150"  # GB
STORAGE = "local-lvm"

# Load VM password from credentials
def load_password():
    creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
    if os.path.exists(creds_file):
        for line in open(creds_file).read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                    return v.strip()
    return os.environ.get("VM_PASSWORD", "")

VM_PASSWORD = load_password()
VM_USER = "mycosoft"

# ── Proxmox API helpers ──────────────────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = f"https://{PROXMOX_HOST}:8006/api2/json"

def pve_get(path):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": PROXMOX_TOKEN}
    )
    r = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(r.read())["data"]

def pve_post(path, data):
    payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=payload,
        headers={
            "Authorization": PROXMOX_TOKEN,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:200]}")
        return None

def pve_delete(path):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": PROXMOX_TOKEN},
        method="DELETE"
    )
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  DELETE HTTP {e.code}: {body[:200]}")
        return None

# ── Check existing VMs ───────────────────────────────────────────────────────
print("=== Checking Proxmox VMs ===")
vms = pve_get(f"/nodes/{NODE}/qemu")
existing = {vm["vmid"]: vm for vm in vms}

if VM_ID in existing:
    status = existing[VM_ID].get("status")
    print(f"VM {VM_ID} already exists (status={status})")
    if status == "running":
        print("VM 191 is already running — skipping creation.")
        # Jump straight to SSH deploy
        SKIP_CREATION = True
    else:
        print("VM 191 exists but not running — starting it.")
        pve_post(f"/nodes/{NODE}/qemu/{VM_ID}/status/start", {})
        SKIP_CREATION = True
else:
    SKIP_CREATION = False
    print(f"VM {VM_ID} does not exist — creating it.")

# ── Check for an Ubuntu cloud-init template to clone ─────────────────────────
if not SKIP_CREATION:
    # Look for an Ubuntu template or existing VM to clone from
    template_id = None
    for vmid, vm in sorted(existing.items()):
        if "ubuntu" in vm.get("name", "").lower() or "template" in vm.get("name", "").lower():
            template_id = vmid
            print(f"Found template: VM {vmid} ({vm.get('name')})")
            break

    # Find an ISO on Proxmox storage
    print("\n=== Looking for Ubuntu ISO ===")
    isos = []
    try:
        isos = pve_get(f"/nodes/{NODE}/storage/local/content")
        ubuntu_isos = [i for i in isos if "ubuntu" in i.get("volid", "").lower() and i.get("content") == "iso"]
        for iso in ubuntu_isos:
            print(f"  Found ISO: {iso['volid']}")
    except Exception as e:
        print(f"  Could not list ISOs: {e}")

    if template_id:
        # Clone from template
        print(f"\n=== Cloning VM {template_id} → VM {VM_ID} ===")
        result = pve_post(f"/nodes/{NODE}/qemu/{template_id}/clone", {
            "newid": VM_ID,
            "name": VM_NAME,
            "full": 1,
            "description": "MYCA Autonomous Workspace — schedule@mycosoft.org",
        })
        print(f"Clone started: {result}")
        print("Waiting 60s for clone to complete...")
        time.sleep(60)
    else:
        # Create new VM from scratch
        print("\n=== Creating VM 191 from scratch ===")
        iso_vol = ubuntu_isos[0]["volid"] if ubuntu_isos else "local:iso/ubuntu-22.04-live-server-amd64.iso"
        result = pve_post(f"/nodes/{NODE}/qemu", {
            "vmid": VM_ID,
            "name": VM_NAME,
            "memory": VM_RAM,
            "cores": VM_CPU,
            "sockets": 1,
            "cpu": "host",
            "ostype": "l26",
            "scsihw": "virtio-scsi-single",
            f"scsi0": f"{STORAGE}:{VM_DISK},discard=on,iothread=1",
            "ide2": f"{iso_vol},media=cdrom",
            "net0": "virtio,bridge=vmbr0,firewall=1",
            "boot": "order=ide2;scsi0",
            "agent": 1,
            "description": "MYCA Autonomous Workspace — schedule@mycosoft.org",
        })
        print(f"VM created: {result}")

        # Start VM
        print("\nStarting VM for OS installation...")
        pve_post(f"/nodes/{NODE}/qemu/{VM_ID}/status/start", {})
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  MANUAL STEP REQUIRED                                       ║
║                                                             ║
║  Open Proxmox console for VM 191:                           ║
║  https://192.168.0.202:8006 → VM 191 → Console             ║
║                                                             ║
║  Install Ubuntu 22.04 with:                                 ║
║    Username: mycosoft                                       ║
║    Hostname: myca-workspace                                 ║
║    Password: {VM_PASSWORD}            ║
║    Static IP: 192.168.0.191/24                              ║
║    Gateway: 192.168.0.1                                     ║
║    Enable SSH                                               ║
║                                                             ║
║  Then re-run this script to deploy the workspace stack.     ║
╚══════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)

# ── Wait for VM SSH to be available ──────────────────────────────────────────
print(f"\n=== Waiting for VM 191 SSH at {VM_IP} ===")
import socket

ssh_ready = False
for attempt in range(30):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((VM_IP, 22))
        s.close()
        ssh_ready = True
        print(f"SSH ready after {attempt * 5}s")
        break
    except:
        print(f"  Waiting... ({attempt * 5}s)")
        time.sleep(5)

if not ssh_ready:
    print("SSH not available. The VM may still be installing Ubuntu.")
    print("Re-run this script once the OS is installed and SSH is enabled.")
    sys.exit(1)

# ── Deploy workspace stack via SSH ───────────────────────────────────────────
print("\n=== Deploying MYCA Workspace Stack on VM 191 ===")
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run(cmd, timeout=60, sudo=False):
    if sudo:
        cmd = f"echo {VM_PASSWORD} | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if err and "sudo" not in err:
        print(f"  STDERR: {err[:100]}")
    return out

# Set static IP
print("Configuring static IP 192.168.0.191...")
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
sftp = ssh.open_sftp()
with sftp.open("/tmp/netplan.yaml", "w") as f:
    f.write(netplan)
sftp.close()
run("cp /tmp/netplan.yaml /etc/netplan/00-installer-config.yaml", sudo=True)
run("netplan apply", sudo=True)

# Install Docker
print("Installing Docker...")
out = run("which docker 2>/dev/null || echo NOT_FOUND")
if "NOT_FOUND" in out:
    run("apt update -qq && apt install -y curl ca-certificates", sudo=True, timeout=120)
    run("curl -fsSL https://get.docker.com | sh", sudo=True, timeout=180)
    run(f"usermod -aG docker {VM_USER}", sudo=True)
    print("Docker installed.")
else:
    print("Docker already installed.")

# Install Docker Compose plugin
run("apt install -y docker-compose-plugin python3-pip git", sudo=True, timeout=120)
run("pip3 install paramiko httpx", timeout=60)

# Create MYCA workspace directory
run("mkdir -p /opt/myca/{credentials/google,data,logs,n8n}", sudo=True)
run(f"chown -R {VM_USER}:{VM_USER} /opt/myca", sudo=True)

# Write docker-compose file
compose = open(os.path.join(os.path.dirname(__file__), "../infra/docker-compose.myca-workspace.yml")).read()
sftp = ssh.open_sftp()
with sftp.open("/opt/myca/docker-compose.yml", "w") as f:
    f.write(compose)

# Write env file
env_template = open(os.path.join(os.path.dirname(__file__), "../infra/.env.myca-workspace")).read()
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_template)
sftp.close()

# Start the stack
print("Starting MYCA workspace Docker stack...")
out = run("cd /opt/myca && docker compose up -d 2>&1", timeout=300)
print(out[-500:])

# Verify
time.sleep(10)
out = run("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
print("\nRunning containers:")
print(out)

# Test workspace API
out = run("curl -s http://localhost:8100/health 2>/dev/null || echo NOT_UP_YET")
print(f"\nWorkspace API health: {out[:100]}")

ssh.close()
print("\n=== VM 191 MYCA Workspace provisioned ===")
print(f"  Workspace API:  http://{VM_IP}:8100")
print(f"  n8n Automation: http://{VM_IP}:5679")
print(f"  Next step: Add Google Service Account JSON to /opt/myca/credentials/google/service_account.json")
