"""Deploy MAS to VM 188 — pull latest code and restart orchestrator."""
import os, paramiko, time

host = "192.168.0.188"
user = "mycosoft"

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
password = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                password = v.strip()
                break

print(f"Deploying MAS to {host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

# Pull latest code
print("Pulling latest code...")
out, err = run("cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main", timeout=30)
print(out[:300])

# Restart MAS orchestrator service
print("Restarting MAS orchestrator...")
out, err = run(f"echo {password} | sudo -S systemctl restart mas-orchestrator", timeout=20)
print("Restart:", out[:100], err[:100])

time.sleep(5)

# Verify health
out, err = run("curl -s http://localhost:8001/health 2>/dev/null | head -100", timeout=10)
print("MAS health:", out[:200])

# Also ensure Ollama stays running
out, err = run("curl -s http://localhost:11434/api/tags | python3 -c \"import sys,json; d=json.load(sys.stdin); print([m['name'] for m in d.get('models',[])])\"", timeout=10)
print("Ollama models:", out.strip()[:100])

ssh.close()
print("Deploy complete.")
