#!/usr/bin/env python3
"""Connect MINDEX API to existing postgres container"""
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
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        ssh.close()
        return out, err
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  CONNECT MINDEX API TO EXISTING POSTGRES")
print("=" * 60)

print("\n[1] Check existing postgres containers...")
out, err = run_ssh_cmd("docker ps --filter name=postgres --format '{{.Names}} {{.Ports}}'")
print(out)

print("\n[2] Test connection to mindex-postgres-data on port 5434...")
out, err = run_ssh_cmd("docker exec mindex-postgres-data psql -U mindex -d mindex -c '\\dt' 2>&1")
print(out or err)

print("\n[3] Get mindex-postgres-data IP on host network...")
# The container is on host network via port mapping, so use host.docker.internal or docker host IP
out, err = run_ssh_cmd("ip route | grep default | awk '{print $3}'")
docker_host_ip = out.strip() if out else "172.17.0.1"
print(f"Docker host IP: {docker_host_ip}")

print("\n[4] Stop old mindex-api and mindex-postgres...")
run_ssh_cmd("docker stop mindex-api mindex-postgres 2>/dev/null; docker rm mindex-api mindex-postgres 2>/dev/null")

print("\n[5] Start mindex-api connected to mindex-postgres-data via host network...")
out, err = run_ssh_cmd("""
docker run -d --name mindex-api \
  --add-host=host.docker.internal:host-gateway \
  -p 8000:8000 \
  -e MINDEX_DB_HOST=host.docker.internal \
  -e MINDEX_DB_PORT=5434 \
  -e MINDEX_DB_USER=mindex \
  -e MINDEX_DB_PASSWORD=mindex \
  -e MINDEX_DB_NAME=mindex \
  -e API_PREFIX=/api/mindex \
  -e 'API_KEYS=["local-dev-key", "sandbox-key"]' \
  mindex-services-mindex-api:latest 2>&1
""")
print(out or err)

print("\n[6] Wait 15s for startup...")
time.sleep(15)

print("\n[7] Test health...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/health")
print(f"Health: {out}")

print("\n[8] Test stats...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(f"Stats: {out}")

print("\n[9] Check logs...")
out, err = run_ssh_cmd("docker logs mindex-api --tail 10 2>&1")
print(out)

print("\n" + "=" * 60)
print("  DONE")
print("=" * 60)
