"""Check Proxmox resources for MYCA VM 191 planning."""
import urllib.request, json, ssl

TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
BASE = "https://192.168.0.202:8006/api2/json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": TOKEN})
    r = urllib.request.urlopen(req, context=ctx, timeout=10)
    return json.loads(r.read())["data"]

# List VMs
vms = api("/nodes/pve/qemu")
print("=== CURRENT VMs ===")
for vm in sorted(vms, key=lambda x: x["vmid"]):
    mem_gb = vm.get("maxmem", 0) // 1024 // 1024 // 1024
    cpu = vm.get("cpus", "?")
    status = vm.get("status", "?")
    name = vm.get("name", "?")
    print(f"  VM {vm['vmid']}: {name:30s} {status:8s} CPU={cpu} RAM={mem_gb}GB")

# Node resources
node = api("/nodes/pve/status")
mem = node["memory"]
total_gb = mem["total"] // 1024 // 1024 // 1024
used_gb = mem["used"] // 1024 // 1024 // 1024
free_gb = total_gb - used_gb
cpus = node["cpuinfo"]["cpus"]
print(f"\n=== NODE RESOURCES ===")
print(f"  RAM: {used_gb}GB used / {total_gb}GB total / {free_gb}GB FREE")
print(f"  CPUs: {cpus} logical")

# Storage
storage = api("/nodes/pve/storage")
for s in storage:
    if s.get("active"):
        avail = s.get("avail", 0) // 1024 // 1024 // 1024
        total = s.get("total", 0) // 1024 // 1024 // 1024
        print(f"  Storage {s['storage']}: {avail}GB free / {total}GB total")
