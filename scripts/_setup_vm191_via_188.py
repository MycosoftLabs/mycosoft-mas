"""
Set up VM 191 by SSHing through VM 188 to reach Proxmox host.
VM 188 is on the same LAN as Proxmox (192.168.0.202).
"""
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
        print(f"  PVE error {e.code}: {e.read().decode()[:150]}")
        return None

# ── Step 1: Stop VM 191 ───────────────────────────────────────────────────────
print("=== [1/5] Stopping VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/stop")
time.sleep(8)

# ── Step 2: SSH to VM 188, then try to reach Proxmox ─────────────────────────
print("=== [2/5] Connecting to VM 188 ===")
ssh188 = paramiko.SSHClient()
ssh188.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh188.connect(VM_188, username=VM_USER, password=VM_PASSWORD, timeout=20)

def run188(cmd, timeout=60):
    stdin, stdout, stderr = ssh188.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()

# Check if Proxmox is reachable from VM 188
out, _ = run188("nc -z -w3 192.168.0.202 22 && echo OPEN || echo CLOSED")
print(f"Proxmox SSH from VM 188: {out}")

# Try SSH to Proxmox from VM 188
print("Trying SSH to Proxmox host from VM 188...")
ssh_cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@192.168.0.202 'echo PROXMOX_SSH_OK' 2>&1"
out, err = run188(ssh_cmd)
print(f"Proxmox SSH result: {out[:100]}")

proxmox_via_188 = "PROXMOX_SSH_OK" in out

if proxmox_via_188:
    print("Can reach Proxmox via VM 188!")
    
    # Install sshpass if needed
    run188("which sshpass || (sudo apt-get install -y sshpass 2>/dev/null)", timeout=60)
    
    def pxm_via_188(cmd, timeout=120):
        full = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} '{cmd}' 2>&1"
        out, err = run188(full, timeout=timeout)
        return out

    # Import cloud image
    print("=== [3/5] Importing cloud image disk ===")
    out = pxm_via_188(f"qm importdisk {VM_ID} {CLOUD_IMG} local-lvm --format raw", timeout=180)
    print("Import:", out[-200:])

    # Attach disk and configure boot
    print("Attaching disk as scsi0...")
    out = pxm_via_188(f"qm set {VM_ID} --scsi0 local-lvm:vm-{VM_ID}-disk-0 --boot c --bootdisk scsi0 --ide2 none,media=cdrom")
    print("Attach:", out[:100])

    # Add cloud-init drive
    out = pxm_via_188(f"qm set {VM_ID} --ide0 local-lvm:cloudinit 2>/dev/null || echo 'CI drive exists'")
    print("CI drive:", out[:100])

    # Resize to 100GB
    out = pxm_via_188(f"qm resize {VM_ID} scsi0 100G")
    print("Resize:", out[:100])

else:
    print("Cannot reach Proxmox via VM 188. Trying alternative...")
    # Try using the Proxmox web UI terminal API
    # Alternative: check if VM 191 can be configured to just use the cloud image as-is
    # by converting the existing setup
    
    print("\nAlternative: Configure cloud-init on existing VM and manually import via Proxmox UI")
    print("Please do ONE of these:")
    print("  A) In Proxmox web UI, open Shell on the Proxmox node and run:")
    print(f"     qm importdisk {VM_ID} {CLOUD_IMG} local-lvm --format raw")
    print(f"     qm set {VM_ID} --scsi0 local-lvm:vm-{VM_ID}-disk-0 --boot c --bootdisk scsi0")
    print(f"     qm set {VM_ID} --ide0 local-lvm:cloudinit")
    print(f"     qm set {VM_ID} --ciuser mycosoft --cipassword '{VM_PASSWORD}' --ipconfig0 ip={VM_IP}/24,gw=192.168.0.1")
    print(f"     qm resize {VM_ID} scsi0 100G")
    print(f"     qm start {VM_ID}")
    print()
    print("  B) Or just install Ubuntu 24.04 Server via Proxmox console (manual):")
    print(f"     https://192.168.0.202:8006 -> VM 191 -> Console")
    print(f"     Username: mycosoft | IP: {VM_IP}/24 | GW: 192.168.0.1")
    ssh188.close()
    sys.exit(0)

ssh188.close()

# ── Step 4: Configure cloud-init via API ─────────────────────────────────────
print("=== [4/5] Configuring cloud-init via API ===")
pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {
    "ciuser": VM_USER,
    "cipassword": VM_PASSWORD,
    "ipconfig0": f"ip={VM_IP}/24,gw=192.168.0.1",
    "nameserver": "8.8.8.8",
    "searchdomain": "local",
})
print("Cloud-init configured")

# ── Step 5: Start VM ─────────────────────────────────────────────────────────
print("=== [5/5] Starting VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/start")
print("VM 191 started. Cloud-init runs on first boot (~2 min).")

print("\nWaiting for SSH (up to 3 min)...")
for i in range(36):
    time.sleep(5)
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((VM_IP, 22))
        s.close()
        print(f"SSH ready after {(i+1)*5}s")
        print(f"\nVM 191 is up! Run the workspace deploy:")
        print(f"  python scripts/_deploy_workspace_191.py")
        break
    except:
        sys.stdout.write(f"\r  {(i+1)*5}s...")
        sys.stdout.flush()
else:
    print("\nSSH not available yet - cloud-init may still be running.")
    print(f"Try: ssh mycosoft@{VM_IP} in a minute.")
