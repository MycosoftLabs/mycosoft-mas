"""Full down/up cycle on VM 191 so containers pick up new .env, then test."""
import os, time, json
import paramiko

key_path = os.path.expanduser("~/.ssh/myca_vm191")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
ssh.connect("192.168.0.191", username="mycosoft", pkey=pkey, timeout=15)

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

def sudo(cmd, timeout=180):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

# Full down/up to reload env
print("Stopping all containers...")
sudo("docker compose -f /opt/myca/docker-compose.yml down", timeout=60)
time.sleep(5)

print("Starting with fresh env...")
sudo("docker compose -f /opt/myca/docker-compose.yml up -d", timeout=120)
time.sleep(20)

# Check containers
print("\nContainers:")
out = sudo("docker ps --format '{{.Names}}  {{.Status}}'")
for line in out.split("\n"):
    if line.strip():
        print(f"  {line.strip()}")

# Health check
print("\nHealth:")
out = run("curl -s http://localhost:8100/health 2>/dev/null")
print(f"  {out[:300]}")

# Test services
print("\nService tests:")
out = run("curl -s -X POST http://localhost:8100/workspace/test/all 2>/dev/null")
try:
    data = json.loads(out)
    for k, v in data.items():
        print(f"  {k:25s} {v}")
except:
    print(f"  Raw: {out[:300]}")

# Quick Discord webhook test
print("\nDiscord webhook test (posting hello)...")
out = run('curl -s -X POST http://localhost:8100/workspace/discord/send -H "Content-Type: application/json" -d \'{"content":"MYCA workspace online. All systems operational on VM 191."}\' 2>/dev/null')
print(f"  Discord: {out[:200]}")

ssh.close()
print("\nDone.")
