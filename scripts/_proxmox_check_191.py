"""Check VM 191 status via Proxmox QEMU Guest Agent and fix SSH."""
import os, json, ssl, time, urllib.request
from pathlib import Path

def load_creds():
    cf = Path(__file__).parent.parent / ".credentials.local"
    if cf.exists():
        for line in cf.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_creds()
pw = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD", ""))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PROXMOX = "https://192.168.0.105:8006"
VMID = 191
NODE = "proxmox"

# Authenticate
print("Authenticating with Proxmox...")
data = f"username=root@pam&password={pw}".encode()
req = urllib.request.Request(f"{PROXMOX}/api2/json/access/ticket", data=data)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        td = json.loads(r.read().decode())
        ticket = td["data"]["ticket"]
        csrf = td["data"]["CSRFPreventionToken"]
        print("  Proxmox auth: OK")
except Exception as e:
    print(f"  Proxmox auth FAILED: {e}")
    exit(1)

def pve_exec(cmd_str, wait=5):
    """Execute command on VM via qemu-agent."""
    body = json.dumps({"command": cmd_str}).encode()
    req = urllib.request.Request(
        f"{PROXMOX}/api2/json/nodes/{NODE}/qemu/{VMID}/agent/exec",
        data=body,
        headers={
            "Cookie": f"PVEAuthCookie={ticket}",
            "CSRFPreventionToken": csrf,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        pid = json.loads(r.read().decode()).get("data", {}).get("pid")

    time.sleep(wait)

    req2 = urllib.request.Request(
        f"{PROXMOX}/api2/json/nodes/{NODE}/qemu/{VMID}/agent/exec-status?pid={pid}",
        headers={"Cookie": f"PVEAuthCookie={ticket}"},
    )
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r2:
        result = json.loads(r2.read().decode()).get("data", {})
        return result.get("out-data", ""), result.get("err-data", ""), result.get("exited", 0)

# 1. Check VM status
print("\n--- VM 191 Status ---")
try:
    out, err, _ = pve_exec("whoami && uptime && hostname")
    print(f"  {out.strip()}")
except Exception as e:
    print(f"  QEMU agent exec failed: {e}")
    print("  The QEMU guest agent may not be installed on VM 191.")
    print("  Trying Proxmox VM status API instead...")
    req = urllib.request.Request(
        f"{PROXMOX}/api2/json/nodes/{NODE}/qemu/{VMID}/status/current",
        headers={"Cookie": f"PVEAuthCookie={ticket}"},
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        status = json.loads(r.read().decode()).get("data", {})
        print(f"  VM status: {status.get('status')}")
        print(f"  CPU: {status.get('cpu', 0)*100:.1f}%")
        print(f"  Memory: {status.get('mem', 0)/(1024**3):.1f}GB / {status.get('maxmem', 0)/(1024**3):.1f}GB")
        print(f"  Uptime: {status.get('uptime', 0)}s")
    exit(0)

# 2. Check services
print("\n--- Services on 191 ---")
try:
    out, err, _ = pve_exec("systemctl is-active myca-os 2>/dev/null; systemctl is-active myca-workspace 2>/dev/null; docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null")
    print(f"  {out.strip()}")
    if err:
        print(f"  stderr: {err[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Check SSH config
print("\n--- SSH Config ---")
try:
    out, err, _ = pve_exec("cat /etc/ssh/sshd_config | grep -E '^(PasswordAuthentication|PubkeyAuthentication|PermitRootLogin)' 2>/dev/null")
    print(f"  {out.strip()}")
except Exception as e:
    print(f"  Error: {e}")

# 4. Fix SSH to allow password auth
print("\n--- Fixing SSH to allow password auth ---")
try:
    out, err, _ = pve_exec(
        "sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config && "
        "sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && "
        "grep PasswordAuthentication /etc/ssh/sshd_config && "
        "systemctl restart sshd && echo SSH_RESTARTED",
        wait=5,
    )
    print(f"  {out.strip()}")
    if err:
        print(f"  stderr: {err[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# 5. Check ports
print("\n--- Open Ports ---")
try:
    out, err, _ = pve_exec("ss -tlnp 2>/dev/null | head -20")
    print(f"  {out.strip()}")
except Exception as e:
    print(f"  Error: {e}")

print("\nDone.")
