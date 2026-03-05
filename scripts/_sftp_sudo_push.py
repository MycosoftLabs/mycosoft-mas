"""Push LLM files via SFTP to /tmp then sudo-cp into place."""
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

files = [
    ("mycosoft_mas/llm/frontier_router.py",       "mycosoft_mas/llm/frontier_router.py"),
    ("mycosoft_mas/consciousness/deliberation.py", "mycosoft_mas/consciousness/deliberation.py"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)
sftp = ssh.open_sftp()

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

for local_rel, remote_rel in files:
    local_path = os.path.join(repo_local, local_rel)
    tmp_path = f"/tmp/{os.path.basename(local_rel)}"
    dest_path = f"{repo_remote}/{remote_rel}"

    # Upload to /tmp (writable)
    print(f"Uploading {local_rel} -> {tmp_path}")
    sftp.put(local_path, tmp_path)

    # Sudo-copy to final destination
    print(f"Sudo-copying to {dest_path}")
    out = run(f"echo {password} | sudo -S cp {tmp_path} {dest_path} && echo OK")
    print("  Result:", out[:80])

sftp.close()

# Verify
count = run(f"grep -c 'OLLAMA_BASE_URL' {repo_remote}/mycosoft_mas/llm/frontier_router.py 2>/dev/null")
print(f"\nOllama code in frontier_router: {count} occurrences")
count2 = run(f"grep -c 'get_frontier_router' {repo_remote}/mycosoft_mas/consciousness/deliberation.py 2>/dev/null")
print(f"Singleton in deliberation: {count2} occurrences")

# Restart MAS
print("\nRestarting MAS orchestrator...")
run(f"echo {password} | sudo -S systemctl restart mas-orchestrator 2>&1")
time.sleep(10)
health = run("curl -s http://localhost:8001/health 2>/dev/null")
print("MAS health:", health[:200])

ssh.close()
print("Done.")
