"""SSH to VM 188: add N8N_API_KEY to n8n container, recreate, verify, sync."""
import io
import os
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = ""
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                pw = v.strip()
                break
pw = pw or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")

import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

results = {}

# 1. Find n8n container(s)
out, err = run("docker ps -a --format '{{.Names}}' | grep -i n8n || true")
containers = [c.strip() for c in out.strip().splitlines() if c.strip()]
results["containers"] = containers
container_name = containers[0] if containers else None

if not container_name:
    print("ERROR: No n8n container found")
    client.close()
    exit(1)

# 2. Inspect container
out, err = run(f"docker inspect {container_name} 2>/dev/null | head -200")
results["inspect"] = out[:1500] if out else err

# 3. Read MAS .env for N8N_API_KEY
out, err = run("grep -E '^N8N_API_KEY=' /home/mycosoft/mycosoft/mas/.env 2>/dev/null || grep N8N /home/mycosoft/mycosoft/mas/.env 2>/dev/null || echo 'N8N_API_KEY not found'")
env_line = out.strip()
n8n_key = ""
if "N8N_API_KEY=" in env_line:
    n8n_key = env_line.split("=", 1)[1].strip()
results["env_n8n_key"] = n8n_key[:20] + "..." if n8n_key else "NOT FOUND"

# Fallback: use local .credentials.local N8N_API_KEY if MAS .env doesn't have it
if not n8n_key and creds.exists():
    for line in creds.read_text().splitlines():
        if line.strip().startswith("N8N_API_KEY="):
            n8n_key = line.split("=", 1)[1].strip()
            break
    if n8n_key:
        results["env_n8n_key"] = "(from local .credentials.local)"

# 4. Find docker-compose for n8n
out, err = run("""
for d in /opt/mycosoft /home/mycosoft /home/mycosoft/mycosoft /home/mycosoft/mycosoft/mas; do
  if [ -d "$d" ]; then
    for f in "$d"/*.yml "$d"/*.yaml "$d"/docker-compose*.yml "$d"/docker-compose*.yaml "$d"/compose*.yml 2>/dev/null; do
      [ -f "$f" ] && grep -l -i n8n "$f" 2>/dev/null
    done
  fi
done 2>/dev/null | head -5
""")
compose_files = [f.strip() for f in out.strip().splitlines() if f.strip()]
# Also check common locations
out2, _ = run("find /opt /home/mycosoft -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' -o -name 'compose*.yml' 2>/dev/null | xargs grep -l -i n8n 2>/dev/null | head -5")
for f in out2.strip().splitlines():
    if f.strip() and f.strip() not in compose_files:
        compose_files.append(f.strip())
compose_path = compose_files[0] if compose_files else None
results["compose_path"] = compose_path or "NOT FOUND"

# 5. Add N8N_API_KEY to compose (if we have key and compose)
key_added = False
if n8n_key and compose_path:
    out, _ = run(f"cat '{compose_path}'")
    if "N8N_API_KEY" in out:
        key_added = True
    else:
        # Upload helper script via SFTP, run with key in env
        import base64
        key_b64 = base64.b64encode(n8n_key.encode()).decode()
        py_content = f'''import base64, os, sys
key = base64.b64decode(os.environ.get("K", "")).decode()
path = "{compose_path}"
if not key:
    print("NO_KEY", file=sys.stderr)
    sys.exit(1)
with open(path) as f:
    lines = f.readlines()
new_lines = []
in_n8n, done = False, False
for line in lines:
    new_lines.append(line)
    if "n8n:" in line:
        in_n8n = True
    elif in_n8n and "environment:" in line:
        indent = len(line) - len(line.lstrip())
        new_lines.append(" " * (indent + 2) + "- N8N_API_KEY=" + key + "\\n")
        done = True
if done:
    with open(path, "w") as f:
        f.writelines(new_lines)
    print("ADDED")
else:
    print("SKIP")
'''
        sftp = client.open_sftp()
        try:
            sftp.putfo(io.BytesIO(py_content.encode("utf-8")), "/tmp/_add_n8n_key.py")
        finally:
            sftp.close()
        out, err = run(f"K='{key_b64}' python3 /tmp/_add_n8n_key.py 2>&1")
        run("rm -f /tmp/_add_n8n_key.py")
        key_added = "ADDED" in out
        out2, _ = run(f"grep N8N_API_KEY '{compose_path}' 2>/dev/null || true")
        if out2.strip():
            key_added = True

results["key_added"] = key_added

# 6. Recreate n8n container
compose_dir = str(Path(compose_path).parent) if compose_path else None
recreate_ok = False
if compose_path and compose_dir:
    out, err = run(f"cd '{compose_dir}' && docker compose up -d n8n --force-recreate 2>&1 || docker-compose up -d n8n --force-recreate 2>&1")
    recreate_ok = "Started" in out or "Recreated" in out or "Creating" in out or "done" in out.lower()
    results["recreate_out"] = out[:500]

# 7. Verify N8N_API_KEY in container
# Container name might have changed after recreate - find again
out, _ = run("docker ps -a --format '{{.Names}}' | grep -i n8n | head -1")
container_name = out.strip() if out.strip() else container_name
out, err = run(f"docker exec {container_name} printenv N8N_API_KEY 2>/dev/null || echo 'NOT_SET'")
key_in_container = out.strip()
results["key_in_container"] = "SET" if key_in_container and key_in_container != "NOT_SET" else "NOT_SET"

# 8. Trigger sync
out, err = run("curl -s -X POST http://127.0.0.1:8001/api/workflows/sync-both -H 'Content-Type: application/json' -d '{}'")
results["sync_result"] = out[:500] if out else err[:500]

client.close()

# Report
print("=== RESULTS ===")
print("Container name:", container_name)
print("Compose path:", results["compose_path"])
print("N8N_API_KEY from MAS .env:", results["env_n8n_key"])
print("N8N_API_KEY added to compose:", results["key_added"])
print("N8N_API_KEY in container:", results["key_in_container"])
print("Sync result:", results["sync_result"][:300] if results.get("sync_result") else "N/A")
