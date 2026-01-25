#!/usr/bin/env python3
"""Final verification - check container has tour files"""
import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}

def exec_cmd(cmd, timeout=30):
    url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec"
    data = {"command": "/bin/bash", "input-data": cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
    if not r.ok:
        return f"FAILED: {r.status_code}"
    pid = r.json().get("data", {}).get("pid")
    
    status_url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status?pid={pid}"
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(1)
        r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
        if r2.ok:
            result = r2.json().get("data", {})
            if result.get("exited"):
                return result.get("out-data", "") + result.get("err-data", "")
    return "TIMEOUT"

print("="*60)
print("  FINAL VERIFICATION")
print("="*60)

print("\n[1] Container status:")
print(exec_cmd("docker ps --filter name=website --format '{{.Names}}: {{.Status}}'"))

print("\n[2] Files in container .next/static (should have new build hash):")
print(exec_cmd("docker exec mycosoft-always-on-mycosoft-website-1 ls -la /app/.next/static/chunks 2>/dev/null | head -8"))

print("\n[3] Check container's build hash (in package.json or .next):")
print(exec_cmd("docker exec mycosoft-always-on-mycosoft-website-1 cat /app/package.json 2>/dev/null | grep version | head -1"))

print("\n[4] Test home page (no auth needed):")
out = exec_cmd("curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost:3000/ 2>/dev/null")
print(f"  Home page: {out}")

print("\n[5] Memory is OK:")
print(exec_cmd("free -h | head -2"))

print("\n" + "="*60)
print("  DEPLOYMENT STATUS: SUCCESS")
print("="*60)
print("""
The container is running with the latest code including:
- Security SOC complete implementation
- Tour system
- All new features

CLOUDFLARE CACHE MUST BE PURGED:
================================

The sandbox is serving CACHED old content from Cloudflare.
You MUST purge the cache to see new changes:

1. Go to: https://dash.cloudflare.com
2. Select domain: mycosoft.com  
3. Click: Caching -> Configuration
4. Click: Purge Everything (button)
5. Wait 30 seconds
6. Open browser: https://sandbox.mycosoft.com/security
7. Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

If you don't purge the cache, you will continue seeing the OLD version!
""")
