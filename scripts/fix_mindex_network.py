#!/usr/bin/env python3
"""Fix MINDEX network connectivity"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_ssh_cmd(cmd, timeout=120):
    """Run command via SSH"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30, banner_timeout=30)
        print(f"  $ {cmd[:80]}...")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        ssh.close()
        if out:
            for line in out.strip().split('\n')[:15]:
                print(f"    {line}")
        if err and 'warning' not in err.lower():
            for line in err.strip().split('\n')[:5]:
                print(f"    [ERR] {line}")
        return out, err
    except Exception as e:
        print(f"  [ERR] {e}")
        return None, str(e)

print("=" * 60)
print("  MINDEX NETWORK FIX")
print("=" * 60)

print("\n[1] Check Docker networks...")
run_ssh_cmd("docker network ls | grep mindex")

print("\n[2] Inspect mindex network...")
run_ssh_cmd("docker network inspect mindex-services_mindex-network 2>/dev/null | grep -A5 Containers || echo 'Network not found'")

print("\n[3] Check if containers are on same network...")
run_ssh_cmd("docker inspect mindex-api --format '{{.NetworkSettings.Networks}}' 2>/dev/null | head -3")
run_ssh_cmd("docker inspect mindex-postgres --format '{{.NetworkSettings.Networks}}' 2>/dev/null | head -3")

print("\n[4] Get mindex-postgres IP address...")
out, err = run_ssh_cmd("docker inspect mindex-postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'")
postgres_ip = out.strip() if out else ""
print(f"    Postgres IP: {postgres_ip}")

print("\n[5] Restart mindex-api with direct IP if needed...")
if postgres_ip:
    run_ssh_cmd(f"""
docker stop mindex-api 2>/dev/null
docker rm mindex-api 2>/dev/null
docker run -d --name mindex-api \
  --network mindex-services_mindex-network \
  -p 8000:8000 \
  -e MINDEX_DB_HOST={postgres_ip} \
  -e MINDEX_DB_PORT=5432 \
  -e MINDEX_DB_USER=mindex \
  -e MINDEX_DB_PASSWORD=mindex \
  -e MINDEX_DB_NAME=mindex \
  -e API_PREFIX=/api/mindex \
  -e 'API_KEYS=["local-dev-key", "sandbox-key"]' \
  mindex-services-mindex-api:latest
""")

print("\n[6] Wait 15s...")
time.sleep(15)

print("\n[7] Test API connection...")
run_ssh_cmd("curl -s http://localhost:8000/api/mindex/health")

print("\n[8] Test stats...")
run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats | head -c 300")

print("\n[9] Check logs...")
run_ssh_cmd("docker logs mindex-api --tail 10 2>&1")

print("\n" + "=" * 60)
print("  NETWORK FIX COMPLETE")
print("=" * 60)
