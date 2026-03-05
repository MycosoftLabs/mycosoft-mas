"""Force pull latest MAS code on VM 188 and restart."""
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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

# Find the MAS repo
out, _ = run("find /home/mycosoft -name 'frontier_router.py' 2>/dev/null | head -3")
print("frontier_router locations:", out.strip())

out2, _ = run("find /home/mycosoft /opt -name 'myca_main.py' 2>/dev/null | head -3")
print("myca_main locations:", out2.strip())

# Try common paths
for path in ["/home/mycosoft/mycosoft/mas", "/home/mycosoft/mas", "/opt/mycosoft/mas"]:
    out3, _ = run(f"ls {path}/mycosoft_mas/llm/frontier_router.py 2>/dev/null")
    if "frontier_router.py" in out3:
        print(f"MAS at: {path}")
        repo_path = path
        break
else:
    print("MAS repo not found at expected paths")
    ssh.close()
    exit(1)

# Pull latest
print(f"Pulling latest at {repo_path}...")
out4, err4 = run(f"cd {repo_path} && git fetch origin && git reset --hard origin/main && git log --oneline -2", timeout=30)
print("Pull result:", out4[:300])
if err4: print("Err:", err4[:100])

# Restart service
print("Restarting mas-orchestrator...")
out5, err5 = run(f"echo {password} | sudo -S systemctl restart mas-orchestrator", timeout=20)
print("Restart:", out5[:100], err5[:100])

time.sleep(6)

# Verify new code is present
out6, _ = run(f"grep -c 'OLLAMA_BASE_URL' {repo_path}/mycosoft_mas/llm/frontier_router.py 2>/dev/null")
print("Ollama code present (grep count):", out6.strip())

out7, _ = run("curl -s http://localhost:8001/health 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))\" 2>/dev/null")
print("MAS status:", out7.strip())

ssh.close()
print("Done.")
