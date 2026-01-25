#!/usr/bin/env python3
"""
DISCOVER VM STATE - Find actual file paths and container status
"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def exec_cmd(cmd, timeout=60):
    """Execute command and return output"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return f"EXEC FAILED: {r.status_code}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return "NO PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if r2.ok:
                result = r2.json().get("data", {})
                if result.get("exited"):
                    stdout = result.get("out-data", "")
                    stderr = result.get("err-data", "")
                    # Try to decode base64 if needed
                    try:
                        if stdout and not stdout.isprintable():
                            stdout = base64.b64decode(stdout).decode('utf-8', errors='replace')
                    except:
                        pass
                    return stdout + stderr
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

print("=" * 70)
print("  DISCOVERING VM 103 STATE")
print("=" * 70)

# Check what docker-compose files exist
print("\n[1] DOCKER COMPOSE FILES:")
print(exec_cmd("""
find /home/mycosoft /opt/mycosoft -name 'docker-compose*.yml' 2>/dev/null | head -20
"""))

# Check website repo locations
print("\n[2] WEBSITE REPOSITORY:")
print(exec_cmd("""
for dir in /opt/mycosoft/website /home/mycosoft/mycosoft/website /home/mycosoft/mycosoft/WEBSITE/website; do
    if [ -d "$dir" ]; then
        echo "FOUND: $dir"
        cd "$dir" && git log --oneline -1 2>/dev/null || echo "  (not a git repo)"
    fi
done
"""))

# Check MAS repo locations
print("\n[3] MAS REPOSITORY:")
print(exec_cmd("""
for dir in /opt/mycosoft/mas /home/mycosoft/mycosoft/mas /home/mycosoft/mycosoft/mas_old/mas; do
    if [ -d "$dir" ]; then
        echo "FOUND: $dir"
        if [ -f "$dir/docker-compose.always-on.yml" ]; then
            echo "  HAS docker-compose.always-on.yml"
        fi
    fi
done
"""))

# Check running containers
print("\n[4] RUNNING CONTAINERS:")
print(exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -15"))

# Check Docker images
print("\n[5] DOCKER IMAGES (website related):")
print(exec_cmd("docker images | grep -E 'website|mycosoft' | head -10"))

# Check memory
print("\n[6] MEMORY STATUS:")
print(exec_cmd("free -h | head -3"))

# Check disk space
print("\n[7] DISK SPACE:")
print(exec_cmd("df -h / | head -2"))

# Check the .env file
print("\n[8] ENVIRONMENT FILE:")
print(exec_cmd("""
for f in /opt/mycosoft/.env /home/mycosoft/mycosoft/mas/.env; do
    if [ -f "$f" ]; then
        echo "FOUND: $f"
        echo "  Contains SUPABASE_URL: $(grep -c SUPABASE_URL $f 2>/dev/null || echo 0)"
        echo "  Contains NEXTAUTH_SECRET: $(grep -c NEXTAUTH_SECRET $f 2>/dev/null || echo 0)"
    fi
done
"""))

print("\n" + "=" * 70)
print("  DISCOVERY COMPLETE")
print("=" * 70)
