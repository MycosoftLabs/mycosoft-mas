"""Fix VM 191 disk: swap scsi0 from blank disk to cloud image disk via Proxmox API."""
import json, ssl, time, socket, sys
import urllib.request, urllib.parse

TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
BASE = "https://192.168.0.202:8006/api2/json"
NODE = "pve"
VM_ID = 191
VM_IP = "192.168.0.191"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

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
        body = e.read().decode()
        print(f"  {method} {path} -> HTTP {e.code}: {body[:200]}")
        return None

def pve_get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": TOKEN})
    r = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(r.read())["data"]

# Step 1: Check current config
print("=== Current VM 191 config ===")
cfg = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/config")
for key in sorted(cfg):
    if any(k in key for k in ["scsi", "ide", "boot", "ci", "unused"]):
        print(f"  {key}: {cfg[key]}")

# Step 2: Stop VM
print("\n=== Stopping VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/stop")
for i in range(12):
    time.sleep(5)
    st = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/status/current")
    if st.get("status") == "stopped":
        print(f"  Stopped after {(i+1)*5}s")
        break
    print(f"  Still {st.get('status')}... {(i+1)*5}s")

# Step 3: Check for unused disks (the cloud image import goes to unused)
print("\n=== Checking for unused disks ===")
cfg = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/config")
unused_disks = {}
for key, val in cfg.items():
    if key.startswith("unused"):
        print(f"  {key}: {val}")
        unused_disks[key] = val

# Step 4: Swap disks
# The imported cloud image may be in unused0 or we need to figure out which is which
# scsi0 currently = vm-191-disk-0 (blank 150GB)
# unused0 likely = vm-191-disk-1 (cloud image ~700MB)
current_scsi0 = cfg.get("scsi0", "")
print(f"\n  Current scsi0: {current_scsi0}")

if unused_disks:
    # Use the first unused disk (cloud image)
    cloud_disk = list(unused_disks.values())[0]
    unused_key = list(unused_disks.keys())[0]
    print(f"  Cloud image disk: {cloud_disk} (was {unused_key})")
    
    # Delete current scsi0 (blank disk)
    print("\n=== Removing blank scsi0 disk ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {"delete": "scsi0"})
    print(f"  Delete scsi0: {result}")
    time.sleep(2)
    
    # Attach cloud image as scsi0
    print("=== Attaching cloud image as scsi0 ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {"scsi0": cloud_disk})
    print(f"  Set scsi0: {result}")
    time.sleep(2)
    
    # Resize to 100GB
    print("=== Resizing disk to 100GB ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/resize", {"disk": "scsi0", "size": "100G"})
    print(f"  Resize: {result}")
    time.sleep(2)
    
elif "disk-1" in current_scsi0:
    print("  scsi0 already points to disk-1 (cloud image)")
else:
    # Try to directly switch scsi0 to disk-1
    # The import likely created vm-191-disk-1
    new_disk = f"local-lvm:vm-{VM_ID}-disk-1"
    print(f"\n  No unused disks found. Trying to set scsi0 to: {new_disk}")
    
    print("=== Removing current scsi0 ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {"delete": "scsi0"})
    print(f"  Delete: {result}")
    time.sleep(2)
    
    print(f"=== Setting scsi0 to {new_disk} ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/config", {"scsi0": new_disk})
    print(f"  Set: {result}")
    time.sleep(2)
    
    print("=== Resizing to 100GB ===")
    result = pve("PUT", f"/nodes/{NODE}/qemu/{VM_ID}/resize", {"disk": "scsi0", "size": "100G"})
    print(f"  Resize: {result}")

# Step 5: Verify config
print("\n=== New config ===")
cfg = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/config")
for key in sorted(cfg):
    if any(k in key for k in ["scsi", "ide", "boot", "ci", "unused"]):
        print(f"  {key}: {cfg[key]}")

# Step 6: Start VM
print("\n=== Starting VM 191 ===")
pve("POST", f"/nodes/{NODE}/qemu/{VM_ID}/status/start")
print("Started. Cloud-init first boot takes ~90 seconds.")

# Step 7: Wait for SSH
print("\nWaiting for SSH...")
for i in range(30):
    time.sleep(5)
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((VM_IP, 22))
        s.close()
        print(f"\nSSH READY after {(i+1)*5}s!")
        print(f"VM 191 is alive at {VM_IP}")
        sys.exit(0)
    except:
        sys.stdout.write(f"\r  {(i+1)*5}s...")
        sys.stdout.flush()

print(f"\nSSH still not up after 150s. Check Proxmox console for VM {VM_ID}.")
