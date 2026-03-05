"""Fix MAS orchestrator container env vars and rebuild if needed."""
import paramiko, os, re, time
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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=pw, timeout=10)

def run(cmd, timeout=30):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

# Get the actual MINDEX PG password
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect("192.168.0.189", username="mycosoft", password=pw, timeout=10)
_, out189, _ = ssh2.exec_command("docker exec mindex-postgres printenv POSTGRES_PASSWORD 2>/dev/null")
mindex_pw = out189.read().decode().strip()
ssh2.close()
print(f"MINDEX PG password length: {len(mindex_pw)}")

# Check how the container was started
out, _ = run("docker inspect myca-orchestrator-new --format '{{json .Config.Cmd}}' 2>/dev/null")
print(f"Container CMD: {out.strip()[:200]}")

out, _ = run("docker inspect myca-orchestrator-new --format '{{.HostConfig.Binds}}' 2>/dev/null")
print(f"Binds: {out.strip()[:300]}")

# Check if it uses --env-file or -e flags (baked into image vs runtime)
out, _ = run("docker inspect myca-orchestrator-new --format '{{json .Config.Env}}' 2>/dev/null")
env_json = out.strip()
# Redact secrets
redacted = re.sub(r'(PASSWORD[=:])([^",]+)', r'\1***', env_json)
redacted = re.sub(r'(sk-[a-zA-Z0-9_-]{10})[a-zA-Z0-9_-]+', r'\1...REDACTED', redacted)
redacted = re.sub(r'(://mycosoft:)[^@]+', r'\1***@', redacted)
print(f"Container env (redacted): {redacted[:800]}")

# The container likely has stale env. We need to recreate it.
# Get the image name
out, _ = run("docker inspect myca-orchestrator-new --format '{{.Config.Image}}' 2>/dev/null")
image = out.strip()
print(f"Image: {image}")

# Stop and recreate with correct env
print("\nRecreating container with correct MINDEX password...")
correct_url = f"postgresql://mycosoft:{mindex_pw}@192.168.0.189:5432/mindex"

# Get all current env vars to preserve them
out, _ = run("docker inspect myca-orchestrator-new --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null")
env_lines = [l.strip() for l in out.splitlines() if l.strip()]

# Replace the broken ones
new_env = []
for line in env_lines:
    if line.startswith("MINDEX_DATABASE_URL="):
        new_env.append(f"MINDEX_DATABASE_URL={correct_url}")
    elif line.startswith("MINDEX_DB_PASSWORD="):
        new_env.append(f"MINDEX_DB_PASSWORD={mindex_pw}")
    else:
        new_env.append(line)

# Also update the .env file for future rebuilds
run(f"sed -i 's|^MINDEX_DATABASE_URL=.*|MINDEX_DATABASE_URL={correct_url}|' /home/mycosoft/mycosoft/mas/.env")
run(f"sed -i 's|^MINDEX_DB_PASSWORD=.*|MINDEX_DB_PASSWORD={mindex_pw}|' /home/mycosoft/mycosoft/mas/.env")

# Get exposed ports
out, _ = run("docker inspect myca-orchestrator-new --format '{{json .HostConfig.PortBindings}}' 2>/dev/null")
print(f"Port bindings: {out.strip()[:200]}")

# Stop old container
print("Stopping old container...")
run("docker stop myca-orchestrator-new", timeout=15)
run("docker rm myca-orchestrator-new", timeout=10)

# Build env flags
env_flags = " ".join(f'-e "{l}"' for l in new_env)

# Start new container with corrected env
start_cmd = f"docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 --env-file /home/mycosoft/mycosoft/mas/.env {image}"
print(f"Starting with: docker run ... --env-file .env {image}")
out, err = run(start_cmd, timeout=30)
print(f"  stdout: {out.strip()[:100]}")
if err:
    print(f"  stderr: {err.strip()[:200]}")

# Wait for startup
print("Waiting 8s for startup...")
time.sleep(8)

# Health check
import urllib.request
try:
    with urllib.request.urlopen("http://192.168.0.188:8001/health", timeout=10) as r:
        data = r.read().decode()
        if "unhealthy" not in data:
            print(f"MAS HEALTH: HEALTHY")
        else:
            # Parse components
            import json
            h = json.loads(data)
            for c in h.get("components", []):
                print(f"  {c['name']}: {c['status']} {c.get('message','')[:80]}")
except Exception as e:
    print(f"Health check failed: {e}")

ssh.close()
print("\nDone.")
