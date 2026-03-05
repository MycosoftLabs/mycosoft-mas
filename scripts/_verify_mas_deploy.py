"""Verify MAS deploy — check git hash, service status, LLM router."""
import os, json, paramiko, time

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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    return out.strip()

# Check git hash on VM matches what we pushed
git_hash = run("cd /home/mycosoft/mycosoft/mas && git log --oneline -3")
print("Git log on VM:\n", git_hash)

# Check service status
svc = run("systemctl is-active mas-orchestrator 2>/dev/null || echo unknown")
print("Service status:", svc)

# Check MAS health
time.sleep(8)
health = run("curl -s http://localhost:8001/health 2>/dev/null")
print("MAS health:", health[:400])

# Check Ollama models
ollama = run("curl -s http://localhost:11434/api/tags 2>/dev/null")
print("Ollama tags:", ollama[:200])

# Test Ollama inference directly
print("\nTesting Ollama inference...")
test_cmd = (
    "curl -s -X POST http://localhost:11434/api/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"model\":\"llama3.2:3b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in 5 words\"}],\"stream\":false}'"
)
result = run(test_cmd, timeout=30)
try:
    data = json.loads(result)
    msg = data.get("message", {}).get("content", "")
    print("Ollama response:", msg[:200])
except Exception as e:
    print("Parse error:", e, "Raw:", result[:200])

ssh.close()
