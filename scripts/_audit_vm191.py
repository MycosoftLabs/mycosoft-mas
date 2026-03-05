"""Full audit of VM 191 — what's running, what's missing, what's needed."""
import os, json, paramiko

key_path = os.path.expanduser("~/.ssh/myca_vm191")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
ssh.connect("192.168.0.191", username="mycosoft", pkey=pkey, timeout=15)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

print("=" * 60)
print("VM 191 MYCA WORKSPACE AUDIT")
print("=" * 60)

# System
print("\n--- SYSTEM ---")
print("Hostname:", run("hostname"))
print("Uptime:", run("uptime"))
print("IP:", run("hostname -I"))
print("Disk:", run("df -h / | tail -1"))
print("RAM:", run("free -h | grep Mem"))

# Docker
print("\n--- DOCKER ---")
print("Docker:", run("which docker 2>/dev/null && docker --version || echo NOT INSTALLED"))
print("Compose:", run("docker compose version 2>/dev/null || echo NOT AVAILABLE"))
containers = run("sudo docker ps -a --format '{{.Names}}|{{.Status}}|{{.Ports}}' 2>/dev/null")
if containers:
    print("Containers:")
    for line in containers.split("\n"):
        parts = line.split("|")
        if len(parts) >= 2:
            print(f"  {parts[0]:25s} {parts[1]:20s} {parts[2] if len(parts) > 2 else ''}")
else:
    print("Containers: NONE")

# Service health
print("\n--- SERVICE HEALTH ---")
checks = {
    "Workspace API (8100)": "curl -s http://localhost:8100/health 2>/dev/null || echo DOWN",
    "n8n (5679)": "curl -s http://localhost:5679/healthz 2>/dev/null || echo DOWN",
    "PostgreSQL (5433)": "sudo docker exec myca-postgres pg_isready 2>/dev/null && echo UP || echo DOWN",
    "Redis (6380)": "sudo docker exec myca-redis redis-cli ping 2>/dev/null || echo DOWN",
}
for name, cmd in checks.items():
    result = run(cmd)
    print(f"  {name:30s} {result[:80]}")

# Connectivity to other VMs
print("\n--- CONNECTIVITY TO OTHER VMs ---")
vms = {
    "MAS Brain (188:8001)": "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.188:8001/health 2>/dev/null",
    "MINDEX (189:8000)": "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.189:8000/health 2>/dev/null",
    "Bridge (190:8999)": "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.190:8999/health 2>/dev/null",
    "Website (187:3000)": "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.187:3000 2>/dev/null",
}
for name, cmd in vms.items():
    result = run(cmd)
    print(f"  {name:30s} {result}")

# Files on disk
print("\n--- /opt/myca CONTENTS ---")
print(run("find /opt/myca -maxdepth 3 -type f 2>/dev/null | sort"))

# Env file
print("\n--- .ENV CONTENTS (keys only) ---")
env = run("cat /opt/myca/.env 2>/dev/null")
if env:
    for line in env.split("\n"):
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            has_val = "SET" if val.strip() and val.strip() not in ("", "''", '""') else "EMPTY"
            print(f"  {key.strip():40s} {has_val}")
else:
    print("  NO .ENV FILE")

# Google credentials
print("\n--- GOOGLE SERVICE ACCOUNT ---")
print(run("test -f /opt/myca/credentials/google/service_account.json && echo EXISTS || echo MISSING"))

# Git
print("\n--- GIT ---")
print("User:", run("git config --global user.name 2>/dev/null || echo NOT SET"))
print("Email:", run("git config --global user.email 2>/dev/null || echo NOT SET"))

# Node.js / Claude Code
print("\n--- TOOLS ---")
print("Node:", run("which node 2>/dev/null && node --version || echo NOT INSTALLED"))
print("npm:", run("which npm 2>/dev/null && npm --version || echo NOT INSTALLED"))
print("Python:", run("python3 --version 2>/dev/null || echo NOT INSTALLED"))

# n8n workflows
print("\n--- N8N WORKFLOWS ---")
n8n_wf = run("curl -s http://localhost:5679/api/v1/workflows 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))\" 2>/dev/null || echo 'CANNOT_CHECK'")
print(f"  Workflow count: {n8n_wf}")

# SSH
print("\n--- SSH AUTH ---")
print("Password auth:", run("grep -E '^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null || echo NOT_SET"))

ssh.close()

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
