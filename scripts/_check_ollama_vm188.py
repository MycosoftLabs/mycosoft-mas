"""Check Ollama pull progress on MAS VM 188."""
import os, sys, json, paramiko

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
ssh.connect(host, username=user, password=password, timeout=15)

def run(cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

# Check tags
out, _ = run("curl -s http://localhost:11434/api/tags")
print("Tags response:", out[:400])

# Check pull log
out2, _ = run("tail -10 /tmp/ollama_pull.log 2>/dev/null")
print("Pull log:", out2[:300])

# Check if process is still pulling
out3, _ = run("pgrep -a ollama | head -5")
print("Ollama procs:", out3[:200])

ssh.close()
