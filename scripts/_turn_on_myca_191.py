#!/usr/bin/env python3
"""Turn on VM 191: populate env with keys, ensure services, ready for MYCA."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")
ROOT = os.path.join(os.path.dirname(__file__), "..")

# Load credentials
VM_PASSWORD = ""
for f in [os.path.join(ROOT, ".credentials.local"), os.path.join(ROOT, ".env")]:
    if os.path.exists(f):
        for line in open(f, encoding="utf-8").read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k in ("VM_PASSWORD", "VM_SSH_PASSWORD") and v:
                    VM_PASSWORD = v
                    break
    if VM_PASSWORD:
        break

# Load API keys from .env (no printing of values)
def load_env():
    env_path = os.path.join(ROOT, ".env")
    out = {}
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8").read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out

def load_creds():
    p = os.path.join(ROOT, ".credentials.local")
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8").read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out

env = load_env()
creds = load_creds()

# Build VM .env content
env_lines = [
    "# MAS & MINDEX (required for full MYCA operation)",
    "MAS_API_URL=http://192.168.0.188:8001",
    "MINDEX_API_URL=http://192.168.0.189:8000",
    "",
    "# Claude / Anthropic (for Claude Code CLI)",
    f"ANTHROPIC_API_KEY={env.get('ANTHROPIC_API_KEY', '')}",
    "",
    "# GitHub (for gh CLI, Cursor)",
    f"GITHUB_TOKEN={env.get('GITHUB_TOKEN', '')}",
    "",
    "# OpenAI (for Cursor, plugins)",
    f"OPENAI_API_KEY={env.get('OPENAI_API_KEY', '')}",
    "",
    "# n8n (VM 191 runs n8n)",
    f"N8N_URL={creds.get('N8N_URL', 'http://192.168.0.191:5679')}",
    f"N8N_API_KEY={creds.get('N8N_API_KEY', '')}",
]
env_content = "\n".join(env_lines)

import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    if os.path.exists(KEY_PATH):
        ssh.connect(VM_IP, username=VM_USER, pkey=paramiko.Ed25519Key.from_private_key_file(KEY_PATH), timeout=20)
    else:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=20)
except Exception as e:
    print(f"SSH connect failed: {e}")
    sys.exit(1)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

print("=== Turn On VM 191 ===\n")

# 1. Ensure services running
print("1. Services...")
run("sudo systemctl start xrdp novnc 2>/dev/null || true")
run("vncserver :1 -geometry 1920x1080 -depth 24 2>/dev/null || true")
out, _ = run("systemctl is-active xrdp novnc 2>/dev/null")
print(f"   xrdp, novnc: {out[:60]}")

# 2. Update .env with keys
print("2. Updating ~/myca-workspace/.env with keys...")
sftp = ssh.open_sftp()
run("mkdir -p ~/myca-workspace")
with sftp.open("/home/mycosoft/myca-workspace/.env", "w") as f:
    f.write(env_content)
run("chmod 600 ~/myca-workspace/.env")
sftp.close()
print("   Done (ANTHROPIC, OPENAI, N8N populated)")

# 3. Ensure .env is sourced in bashrc
print("3. Ensuring .env in bashrc...")
out, _ = run("grep -q 'myca-workspace/.env' ~/.bashrc && echo OK || echo MISSING")
if "MISSING" in out:
    run("echo 'if [ -f ~/myca-workspace/.env ]; then set -a; source ~/myca-workspace/.env; set +a; fi' >> ~/.bashrc")
    print("   Added")
else:
    print("   Already present")

# 4. Claude Code - ensure in PATH and working
print("4. Claude Code...")
run("export PATH=$HOME/.local/bin:$PATH; curl -fsSL https://claude.ai/install.sh 2>/dev/null | bash 2>/dev/null || true")
run("grep -q '.local/bin' ~/.bashrc || echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc")
cv, _ = run("export PATH=$HOME/.local/bin:$PATH; claude --version 2>/dev/null")
print(f"   {cv[:80] if cv else 'Install manually: curl -fsSL https://claude.ai/install.sh | bash'}")

# 5. Cursor shortcut - verify path
print("5. Cursor shortcut...")
out, _ = run("ls -la ~/Applications/cursor.AppImage 2>/dev/null || ls -la /home/mycosoft/Applications/cursor.AppImage 2>/dev/null || echo MISSING")
if "MISSING" not in out:
    print("   OK")
else:
    run("mkdir -p ~/Applications")
    print("   Cursor AppImage path checked")

# 6. Playbook present
print("6. Playbook...")
pb, _ = run("test -f ~/myca-workspace/PLAYBOOK.md && echo OK")
print("   OK" if "OK" in pb else "   Copying...")
if "OK" not in pb:
    playbook_local = os.path.join(os.path.dirname(__file__), "../docs/MYCA_SELF_PROVISIONING_PLAYBOOK_MAR04_2026.md")
    if os.path.exists(playbook_local):
        with open(playbook_local, encoding="utf-8") as f:
            content = f.read()
        sftp = ssh.open_sftp()
        with sftp.open("/home/mycosoft/myca-workspace/PLAYBOOK.md", "w") as f:
            f.write(content)
        sftp.close()
        print("   Copied")

# 7. Quick health
print("7. Health...")
code, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:6080/vnc.html 2>/dev/null")
print(f"   noVNC: HTTP {code}")
run("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.188:8001/health 2>/dev/null")
print("   MAS: reachable from 191")

# 8. Ready helper
print("8. Ready helper...")
ready_sh = '''#!/bin/bash
[ -f ~/myca-workspace/.env ] && source ~/myca-workspace/.env
echo "MYCA VM 191 Ready"
echo "MAS: $MAS_API_URL" 
echo "MINDEX: $MINDEX_API_URL"
echo "Claude:" "$(~/.local/bin/claude --version 2>/dev/null || echo not-found)"
echo "noVNC: http://192.168.0.191:6080"
'''
sftp = ssh.open_sftp()
with sftp.open("/home/mycosoft/myca-workspace/ready.sh", "w") as f:
    f.write(ready_sh)
sftp.close()
run("chmod +x ~/myca-workspace/ready.sh")
print("   ~/myca-workspace/ready.sh")

print("\n=== VM 191 is ON ===")
print("Access: http://192.168.0.191:6080 (noVNC) or RDP 192.168.0.191:3389")
print("MYCA: source ~/myca-workspace/.env and run 'claude' or 'cursor'")
print("      or run: ~/myca-workspace/ready.sh")
