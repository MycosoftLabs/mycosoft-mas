"""Fix MAS postgres connection and check VM 191 status via 188 hop."""
import paramiko, os
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

def ssh_run(host, cmd, timeout=15):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=pw, timeout=10)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    ssh.close()
    return out, err

# 1. Fix MAS PG password -- update .env on 188
print("=" * 60)
print("STEP 1: Fix MAS Postgres connection to MINDEX")
print("=" * 60)

mindex_pg_pw = os.environ.get("MINDEX_DB_PASSWORD", "")
if not mindex_pg_pw:
    print("WARNING: MINDEX_DB_PASSWORD not in local env, checking MINDEX VM...")
    out, _ = ssh_run("192.168.0.189", "docker exec mindex-postgres printenv POSTGRES_PASSWORD 2>/dev/null")
    mindex_pg_pw = out.strip()
    print(f"  Got PG password from MINDEX VM (length={len(mindex_pg_pw)})")

if mindex_pg_pw:
    correct_url = f"postgresql://mycosoft:{mindex_pg_pw}@192.168.0.189:5432/mindex"
    print(f"  Updating MAS .env with correct MINDEX credentials...")
    
    sed_cmd = f"sed -i 's|^MINDEX_DATABASE_URL=.*|MINDEX_DATABASE_URL={correct_url}|' /home/mycosoft/mycosoft/mas/.env"
    sed_cmd2 = f"sed -i 's|^MINDEX_DB_PASSWORD=.*|MINDEX_DB_PASSWORD={mindex_pg_pw}|' /home/mycosoft/mycosoft/mas/.env"
    out, err = ssh_run("192.168.0.188", f"{sed_cmd} && {sed_cmd2}")
    if err:
        print(f"  sed error: {err[:200]}")
    else:
        print("  .env updated")
    
    # Restart MAS container
    print("  Restarting MAS container...")
    out, err = ssh_run("192.168.0.188", "docker restart myca-orchestrator-new", timeout=30)
    print(f"  {out.strip()}")
    
    # Wait and check health
    import time
    time.sleep(5)
    import urllib.request
    try:
        with urllib.request.urlopen("http://192.168.0.188:8001/health", timeout=10) as r:
            data = r.read().decode()
            if "healthy" in data and "unhealthy" not in data:
                print("  MAS health: HEALTHY")
            else:
                print(f"  MAS health: {data[:200]}")
    except Exception as e:
        print(f"  Health check: {e}")
else:
    print("  Could not determine MINDEX PG password")

# 2. Check VM 191 via hop from 188
print()
print("=" * 60)
print("STEP 2: Check VM 191 via SSH hop from 188")
print("=" * 60)

hop_cmd = "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 mycosoft@192.168.0.191 'echo CONNECTED; whoami; uptime; echo ---SERVICES---; systemctl is-active myca-os 2>/dev/null; systemctl is-active myca-workspace 2>/dev/null; echo ---DOCKER---; docker ps --format \"table {{.Names}}\\t{{.Status}}\" 2>/dev/null; echo ---PROCS---; ps aux --no-headers -o comm,args | grep -E \"(python|node|n8n|claude)\" | grep -v grep | head -10; echo ---PORTS---; ss -tlnp 2>/dev/null | grep -E \"(8000|5679|8089|9000)\"' 2>&1"

out, err = ssh_run("192.168.0.188", hop_cmd, timeout=20)
print(out[:1500])
if err:
    print(f"  stderr: {err[:300]}")

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
