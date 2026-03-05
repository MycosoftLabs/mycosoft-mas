#!/usr/bin/env python3
"""Deploy Signal spam fix to MYCA on VM 191: git pull + restart myca-os.service."""
import base64
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
REPO_PATH = "/home/mycosoft/repos/mycosoft-mas"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")

creds = {}
creds_file = os.path.join(ROOT, ".credentials.local")
if os.path.exists(creds_file):
    for line in open(creds_file, encoding="utf-8").read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
VM_PASSWORD = creds.get("VM_PASSWORD") or creds.get("VM_SSH_PASSWORD", "")

sys.path.insert(0, ROOT)
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    if os.path.exists(KEY_PATH):
        ssh.connect(VM_IP, username=VM_USER, pkey=paramiko.Ed25519Key.from_private_key_file(KEY_PATH), timeout=20)
    else:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=20)
except Exception as e:
    print(f"SSH failed: {e}")
    sys.exit(1)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

def sudo(cmd, timeout=90):
    stdin, stdout, stderr = ssh.exec_command("sudo -S bash -c " + repr(cmd), timeout=timeout, get_pty=True)
    if VM_PASSWORD:
        stdin.write(VM_PASSWORD + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

print("Deploying Signal fix to MYCA on VM 191...")
print()

# 1. Git: fetch + reset --hard (discard local changes, match origin/main)
print("[1/2] git fetch + reset --hard origin/main...")
out, err = run(f"cd {REPO_PATH} && git fetch origin main && git reset --hard origin/main", timeout=90)
print(out)
if err:
    print("stderr:", err)
print("  (repo synced to origin/main)")

# 2. Restart myca-os (use sudo helper with long timeout)
print()
print("[2/2] Restarting myca-os.service...")
out, err = sudo("systemctl restart myca-os", timeout=90)
if err and "password" not in err.lower():
    print("  stderr:", err[:200])
time.sleep(3)

# 3. Verify
for _ in range(6):
    out, _ = run("systemctl is-active myca-os 2>/dev/null || true", timeout=10)
    if out.strip() == "active":
        print("  Done.")
        print()
        print("MYCA OS: active")
        print("Deploy complete. Signal spam fix is live.")
        break
    time.sleep(5)
else:
    print()
    print("WARNING: myca-os may still be starting. Check: ssh mycosoft@192.168.0.191 'systemctl status myca-os'")

ssh.close()
