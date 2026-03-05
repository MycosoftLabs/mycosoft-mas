"""Install sshpass on VM 188, then import cloud image and configure VM 191."""
import json, os, ssl, sys, time, socket
import urllib.request, urllib.parse
import paramiko

PROXMOX_HOST = "192.168.0.202"
TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
VM_ID = 191
VM_IP = "192.168.0.191"
VM_188 = "192.168.0.188"
CLOUD_IMG = "/var/lib/vz/template/iso/ubuntu-22.04-server-cloudimg-amd64.img"

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
        headers={"Authorization": TOKEN, "Content-Type": "application/x-www-form-urlencoded" if payload else ""},
        method=method
    )
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        print(f"  PVE {e.code}: {e.read().decode()[:120]}")
        return None

# Connect to VM 188
print("Connecting to VM 188...")
ssh188 = paramiko.SSHClient()
ssh188.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh188.connect(VM_188, username=VM_USER, password=VM_PASSWORD, timeout=20)

def r188(cmd, timeout=120):
    stdin, stdout, stderr = ssh188.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

# Install sshpass
print("Installing sshpass on VM 188...")
out, err = r188(f"echo {VM_PASSWORD} | sudo -S apt-get install -y sshpass 2>&1 | tail -3", timeout=60)
print("sshpass install:", out[:100])

# Verify sshpass works
out, _ = r188("which sshpass")
print("sshpass path:", out)

if not out:
    print("sshpass still not available. Trying snap or direct download...")
    out, _ = r188(f"echo {VM_PASSWORD} | sudo -S apt-get install -y sshpass || pip3 install sshpass 2>&1 | tail -2", timeout=60)

# Now try SSH to Proxmox
print("\nTrying SSH to Proxmox from VM 188...")
ssh_test = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{PROXMOX_HOST} 'hostname; echo OK' 2>&1"
out, err = r188(ssh_test, timeout=15)
print("Proxmox SSH test:", out[:150])

if "OK" not in out:
    # Try without sshpass — maybe key auth works
    out, _ = r188(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes root@{PROXMOX_HOST} 'echo KEY_AUTH_OK' 2>&1")
    print("Key auth test:", out[:100])
    
    if "KEY_AUTH_OK" not in out:
        print("\nCannot SSH to Proxmox. The root password may be different from VM password.")
        print("\nBest option: Run these commands in Proxmox Shell")
        print("(https://192.168.0.202:8006 -> Shell tab):\n")
        print(f"qm stop {VM_ID}")
        print(f"qm importdisk {VM_ID} {CLOUD_IMG} local-lvm --format raw")
        print(f"qm set {VM_ID} --scsi0 local-lvm:vm-{VM_ID}-disk-0 --boot c --bootdisk scsi0 --ide2 none,media=cdrom")
        print(f"qm set {VM_ID} --ide0 local-lvm:cloudinit")
        print(f"qm set {VM_ID} --ciuser mycosoft --cipassword '{VM_PASSWORD}' --ipconfig0 ip={VM_IP}/24,gw=192.168.0.1 --nameserver 8.8.8.8")
        print(f"qm resize {VM_ID} scsi0 100G")
        print(f"qm start {VM_ID}")
        print()
        print("Then re-run: python scripts/_deploy_workspace_to_191.py")
        ssh188.close()
        sys.exit(0)

def pxm(cmd, timeout=180):
    full = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} '{cmd}' 2>&1"
    out, _ = r188(full, timeout=timeout)
    return out

# Stop VM 191
print("\n=== Stopping VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/stop")
time.sleep(8)

# Remove existing blank scsi0 disk
print("=== Removing blank disk from VM 191 ===")
out = pxm(f"qm set {VM_ID} --delete scsi0 2>&1 || echo no_disk")
print("Remove blank disk:", out[:100])

# Import cloud image
print("=== Importing Ubuntu cloud image (this takes 1-2 min) ===")
out = pxm(f"qm importdisk {VM_ID} {CLOUD_IMG} local-lvm --format raw", timeout=300)
print("Import:", out[-200:])

# Attach as scsi0 and configure boot
print("=== Attaching disk and configuring boot ===")
out = pxm(f"qm set {VM_ID} --scsi0 local-lvm:vm-{VM_ID}-disk-0 --boot c --bootdisk scsi0 --ide2 none,media=cdrom")
print("Attach:", out[:100])

# Cloud-init drive
out = pxm(f"qm set {VM_ID} --ide0 local-lvm:cloudinit 2>/dev/null || true")
print("CI drive:", out[:80])

# Resize to 100GB
out = pxm(f"qm resize {VM_ID} scsi0 100G")
print("Resize:", out[:80])

ssh188.close()

# Configure cloud-init via API
print("=== Configuring cloud-init ===")
result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {
    "ciuser": VM_USER,
    "cipassword": VM_PASSWORD,
    "ipconfig0": f"ip={VM_IP}/24,gw=192.168.0.1",
    "nameserver": "8.8.8.8 192.168.0.1",
    "searchdomain": "mycosoft.local",
})
print("Cloud-init config:", result)

# Start VM
print("=== Starting VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/start")
print("VM 191 started. Cloud-init takes ~2 minutes on first boot.")

# Wait for SSH
print("Waiting for SSH...")
for i in range(40):
    time.sleep(5)
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((VM_IP, 22))
        s.close()
        print(f"\nSSH ready after {(i+1)*5}s!")
        print(f"\nVM 191 OS is ready. Now deploy the workspace:")
        print(f"  python scripts/_deploy_workspace_to_191.py")
        break
    except:
        sys.stdout.write(f"\r  {(i+1)*5}s...")
        sys.stdout.flush()
else:
    print(f"\nSSH timeout. Check VM 191 in Proxmox console.")
    print(f"Once SSH is available: python scripts/_deploy_workspace_to_191.py")
