"""Check VM 191 status and config in detail."""
import json, ssl, socket
import urllib.request, urllib.parse

TOKEN = "PVEAPIToken=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
BASE = "https://192.168.0.202:8006/api2/json"
NODE = "pve"
VM_ID = 191
VM_IP = "192.168.0.191"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def pve_get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": TOKEN})
    r = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(r.read())["data"]

# VM status
status = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/status/current")
print(f"VM 191 status: {status.get('status')}")
print(f"  CPU: {status.get('cpu', 0)*100:.1f}%")
print(f"  RAM: {status.get('mem',0)//1024//1024}MB / {status.get('maxmem',0)//1024//1024}MB")
print(f"  Uptime: {status.get('uptime',0)}s")

# VM config
cfg = pve_get(f"/nodes/{NODE}/qemu/{VM_ID}/config")
print(f"\nVM 191 config:")
print(f"  cores: {cfg.get('cores')}, memory: {cfg.get('memory')}MB")
print(f"  boot: {cfg.get('boot')}")
print(f"  bootdisk: {cfg.get('bootdisk')}")
print(f"  scsi0: {cfg.get('scsi0', 'NOT SET')}")
print(f"  ide0: {cfg.get('ide0', 'NOT SET')}")
print(f"  ide2: {cfg.get('ide2', 'NOT SET')}")
print(f"  net0: {cfg.get('net0', 'NOT SET')}")
print(f"  ciuser: {cfg.get('ciuser', 'NOT SET')}")
print(f"  ipconfig0: {cfg.get('ipconfig0', 'NOT SET')}")

# Try TCP ping
print(f"\nTCP connectivity to {VM_IP}:")
for port, name in [(22, "SSH"), (80, "HTTP"), (443, "HTTPS")]:
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect((VM_IP, port))
        s.close()
        print(f"  Port {port} ({name}): OPEN")
    except:
        print(f"  Port {port} ({name}): closed/filtered")

# Check ICMP (ping via OS)
import subprocess
result = subprocess.run(
    ["ping", "-n", "2", "-w", "2000", VM_IP],
    capture_output=True, text=True
)
reachable = "TTL=" in result.stdout
print(f"  ICMP ping: {'reachable' if reachable else 'unreachable'}")
