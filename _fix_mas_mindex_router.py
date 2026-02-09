"""Fix MAS MINDEX router to proxy to real MINDEX API on VM 189."""
import paramiko

HOST = "192.168.0.188"
USER = "mycosoft"
PASS = "Mushroom1!Mushroom1!"

def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("Connected to MAS VM")

# Find the MAS repo
out, _ = run(ssh, "find /opt -name 'mindex_query.py' -path '*/routers/*' 2>/dev/null || find /home -name 'mindex_query.py' -path '*/routers/*' 2>/dev/null")
print(f"Found mindex_query.py at: {out}")

if not out:
    print("Could not find mindex_query.py, checking MAS installation...")
    out2, _ = run(ssh, "ls /opt/mycosoft/ 2>/dev/null && echo '---' && systemctl status mas-orchestrator 2>/dev/null | head -10")
    print(out2)
    
    # Check where the MAS code lives
    out3, _ = run(ssh, "find / -name 'orchestrator.py' -path '*/mycosoft_mas/core/*' 2>/dev/null | head -5")
    print(f"Orchestrator at: {out3}")

# Check if MINDEX API on 189 is accessible from MAS VM
print("\nTesting MINDEX API accessibility from MAS VM...")
out, _ = run(ssh, "curl -s http://192.168.0.189:8000/health 2>/dev/null || echo 'NOT ACCESSIBLE'")
print(f"MINDEX API health from MAS: {out}")

out, _ = run(ssh, "curl -s 'http://192.168.0.189:8000/mindex/species/search?q=amanita&limit=1' 2>/dev/null | head -c 200")
print(f"Species search from MAS: {out[:200]}")

ssh.close()
print("\nDone")
