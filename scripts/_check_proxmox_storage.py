"""Check what's on Proxmox storage — ISOs, templates, cloud images."""
import json, ssl
import urllib.request

PROXMOX_HOST = "192.168.0.202"
TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
BASE = f"https://{PROXMOX_HOST}:8006/api2/json"
NODE = "pve"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def pve_get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": TOKEN})
    r = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(r.read())["data"]

# List all storage
print("=== Storage Pools ===")
storage = pve_get(f"/nodes/{NODE}/storage")
for s in storage:
    print(f"  {s['storage']}: type={s.get('type')} active={s.get('active')}")

# List all ISOs on local storage
print("\n=== ISOs on local storage ===")
try:
    items = pve_get(f"/nodes/{NODE}/storage/local/content")
    for item in items:
        if item.get("content") in ("iso", "vztmpl") or "ubuntu" in item.get("volid","").lower() or "cloud" in item.get("volid","").lower():
            print(f"  {item['volid']}  size={item.get('size',0)//1024//1024}MB")
except Exception as e:
    print(f"  Error: {e}")

# List all VMs + templates
print("\n=== VMs and Templates ===")
vms = pve_get(f"/nodes/{NODE}/qemu")
for vm in sorted(vms, key=lambda x: x["vmid"]):
    is_template = vm.get("template", 0)
    print(f"  VM {vm['vmid']}: {vm.get('name','?'):30s} status={vm.get('status','?'):10s} template={bool(is_template)}")

# Check if VM 191 exists from previous attempt
print("\n=== VM 191 status ===")
vm191 = next((v for v in vms if v["vmid"] == 191), None)
if vm191:
    print(f"  EXISTS: status={vm191.get('status')} name={vm191.get('name')}")
    # Get full config
    try:
        cfg = pve_get(f"/nodes/{NODE}/qemu/191/config")
        print(f"  CPU cores: {cfg.get('cores')}  RAM: {cfg.get('memory')}MB")
        print(f"  Disks: {[k for k in cfg if k.startswith('scsi') or k.startswith('ide')]}")
        print(f"  Net: {cfg.get('net0')}")
    except Exception as e:
        print(f"  Config error: {e}")
else:
    print("  VM 191 does not exist")
