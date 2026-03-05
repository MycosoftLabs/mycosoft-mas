"""Quick diagnostic: check every layer of the MYCA pipeline."""
import os, sys, socket, json
from pathlib import Path

def load_creds():
    cf = Path(__file__).parent.parent / ".credentials.local"
    if cf.exists():
        for line in cf.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def tcp(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True
    except Exception:
        return False

def http_get(url, timeout=5):
    import urllib.request
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()[:500]
    except Exception as e:
        return 0, str(e)[:200]

def ssh_cmd(host, cmd, timeout=10):
    pw = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD", ""))
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username="mycosoft", password=pw, timeout=timeout)
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        ssh.close()
        return out
    except Exception as e:
        return f"SSH_ERROR: {e}"

load_creds()

print("=" * 70)
print("  MYCA FULL PIPELINE DIAGNOSTIC")
print("=" * 70)

# 1. Network layer
print("\n--- 1. NETWORK REACHABILITY ---")
vms = {"MAS(188)": "192.168.0.188", "MINDEX(189)": "192.168.0.189", "MYCA(191)": "192.168.0.191", "Sandbox(187)": "192.168.0.187"}
for name, ip in vms.items():
    ssh_ok = tcp(ip, 22)
    print(f"  {name:15s}  SSH={ssh_ok}")

# 2. Service health endpoints
print("\n--- 2. SERVICE HEALTH ---")
endpoints = {
    "MAS Orchestrator (188:8001)": "http://192.168.0.188:8001/health",
    "MINDEX API (189:8000)": "http://192.168.0.189:8000/health",
    "n8n MAS (188:5678)": "http://192.168.0.188:5678/healthz",
    "MYCA FastAPI (191:8000)": "http://192.168.0.191:8000/health",
    "MYCA n8n (191:5679)": "http://192.168.0.191:5679/healthz",
    "Website (187:3000)": "http://192.168.0.187:3000",
}
for name, url in endpoints.items():
    code, body = http_get(url, timeout=5)
    status = "OK" if code == 200 else f"FAIL({code})"
    detail = ""
    if code == 200 and "unhealthy" in body.lower():
        status = "UNHEALTHY"
        detail = body[:100]
    print(f"  {name:35s}  {status:12s}  {detail}")

# 3. VM 188 - MAS internals
print("\n--- 3. MAS VM 188 INTERNALS ---")
if tcp("192.168.0.188", 22):
    out = ssh_cmd("192.168.0.188", "systemctl is-active mas-orchestrator 2>/dev/null && echo ACTIVE || echo INACTIVE; docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | head -10; echo '---'; cat /home/mycosoft/mycosoft/mas/.env 2>/dev/null | grep -E '^(MINDEX|ANTHROPIC|OPENAI|OLLAMA)' | head -5")
    for line in out.strip().splitlines():
        print(f"  {line}")
else:
    print("  SSH not reachable")

# 4. VM 191 - MYCA internals
print("\n--- 4. MYCA VM 191 INTERNALS ---")
if tcp("192.168.0.191", 22):
    out = ssh_cmd("192.168.0.191", "systemctl is-active myca-os 2>/dev/null && echo 'myca-os: ACTIVE' || echo 'myca-os: INACTIVE'; systemctl is-active myca-workspace 2>/dev/null && echo 'workspace: ACTIVE' || echo 'workspace: INACTIVE'; docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | head -10; echo '---PROC---'; ps aux --no-headers | grep -E '(python|node|claude|n8n)' | grep -v grep | awk '{print $11, $12, $13}' | head -15; echo '---ENV---'; cat /opt/myca/.env 2>/dev/null | grep -E '^(ANTHROPIC|DISCORD|SIGNAL|ASANA)' | head -5")
    for line in out.strip().splitlines():
        print(f"  {line}")
else:
    print("  SSH not reachable")

# 5. VM 189 - MINDEX/DB layer
print("\n--- 5. MINDEX VM 189 ---")
if tcp("192.168.0.189", 22):
    out = ssh_cmd("192.168.0.189", "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | head -10")
    for line in out.strip().splitlines():
        print(f"  {line}")
else:
    print("  SSH not reachable")

# 6. Code architecture check
print("\n--- 6. MYCA OS CODE MODULES ---")
myca_os = Path(__file__).parent.parent / "mycosoft_mas" / "myca" / "os"
if myca_os.exists():
    modules = sorted(f.stem for f in myca_os.glob("*.py") if f.stem != "__pycache__")
    print(f"  Modules: {', '.join(modules)}")
else:
    print("  myca/os/ directory NOT FOUND")

# 7. Integration clients check
print("\n--- 7. INTEGRATION CLIENTS ---")
integ = Path(__file__).parent.parent / "mycosoft_mas" / "integrations"
clients = sorted(f.stem for f in integ.glob("*_client.py"))
print(f"  Total clients: {len(clients)}")
print(f"  Latest: {', '.join(clients[-10:])}")

# 8. Agent modules check
print("\n--- 8. AGENT MODULES ---")
agents_dir = Path(__file__).parent.parent / "mycosoft_mas" / "agents"
subdirs = sorted(d.name for d in agents_dir.iterdir() if d.is_dir() and d.name != "__pycache__")
print(f"  Agent categories: {', '.join(subdirs)}")
agent_files = list(agents_dir.rglob("*.py"))
agent_count = len([f for f in agent_files if f.stem not in ("__init__", "__pycache__")])
print(f"  Total agent files: {agent_count}")

print("\n" + "=" * 70)
print("  DIAGNOSTIC COMPLETE")
print("=" * 70)
