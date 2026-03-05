"""Push updated LLM files directly to MAS VM via SFTP, bypassing git."""
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

repo_local = os.path.join(os.path.dirname(__file__), "..")
repo_remote = "/home/mycosoft/mycosoft/mas"

files_to_push = [
    ("mycosoft_mas/llm/frontier_router.py", "mycosoft_mas/llm/frontier_router.py"),
    ("mycosoft_mas/consciousness/deliberation.py", "mycosoft_mas/consciousness/deliberation.py"),
]

print(f"Connecting to {host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)

sftp = ssh.open_sftp()

for local_rel, remote_rel in files_to_push:
    local_path = os.path.join(repo_local, local_rel)
    remote_path = f"{repo_remote}/{remote_rel}"
    print(f"  Pushing {local_rel} -> {remote_path}")
    sftp.put(local_path, remote_path)
    print(f"  OK")

sftp.close()

# Verify Ollama code is present
def run(cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

count = run(f"grep -c 'OLLAMA_BASE_URL' {repo_remote}/mycosoft_mas/llm/frontier_router.py 2>/dev/null")
print(f"\nVerify Ollama code present: {count} occurrences")

count2 = run(f"grep -c 'get_frontier_router' {repo_remote}/mycosoft_mas/consciousness/deliberation.py 2>/dev/null")
print(f"Verify singleton usage: {count2} occurrences in deliberation.py")

# Fix git refs issue on VM and then restart
print("\nFixing git refs and restarting MAS...")
run(f"cd {repo_remote} && git remote prune origin 2>/dev/null || true")
restart_out = run(f"echo {password} | sudo -S systemctl restart mas-orchestrator 2>&1")
print("Restart:", restart_out[:100])

time.sleep(8)
health = run("curl -s http://localhost:8001/health 2>/dev/null")
print("MAS health:", health[:200])

ssh.close()
print("\nDone. Files deployed directly via SFTP.")
