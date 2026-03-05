#!/usr/bin/env python3
"""Fix Proxmox console on VM 191: mouse moves but clicks don't work.

Root cause: The cloud kernel (linux-image-*-cloud-amd64) lacks USB drivers.
Proxmox uses a USB tablet device for mouse input; without USB modules, the
tablet is not detected—mouse position works (sent over VNC) but clicks do not.

Solution: Install the full kernel (linux-image-generic) which includes USB
modules. Then reboot so the new kernel loads.

Ref: https://forum.proxmox.com/threads/mouse-clicks-not-working-in-console.148180/
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")
ROOT = os.path.join(os.path.dirname(__file__), "..")

VM_PASSWORD = ""
for f in [os.path.join(ROOT, ".credentials.local"), os.path.join(ROOT, ".env")]:
    if os.path.exists(f):
        for line in open(f, encoding="utf-8").read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD") and v.strip():
                    VM_PASSWORD = v.strip()
                    break
    if VM_PASSWORD:
        break

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

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

def sudo(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command("sudo -S bash -c " + repr(cmd), timeout=timeout)
    if VM_PASSWORD:
        stdin.write(VM_PASSWORD + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

print("=== Fix Proxmox Console Mouse (VM 191) ===\n")

# 1. Check current kernel
print("1. Checking current kernel...")
out, _ = run("uname -r")
kernel = out.strip()
print(f"   Current kernel: {kernel}")

force = "--yes" in sys.argv or "-y" in sys.argv
if "cloud" not in kernel.lower() and not force:
    print("\n   Kernel does not appear to be a cloud kernel. Mouse issues may have another cause.")
    print("   You can still try installing the full kernel; it may help.")
    ans = input("   Proceed with installing linux-image-generic anyway? [y/N]: ").strip().lower()
    if ans != "y":
        print("   Aborted.")
        sys.exit(0)

# 2. Install full kernel (includes USB drivers)
print("\n2. Installing full kernel (linux-image-generic)...")
out, err = sudo("DEBIAN_FRONTEND=noninteractive apt-get update -qq && apt-get install -y linux-image-generic", timeout=180)
if err and "error" in err.lower() and "0 upgraded" not in out:
    print(f"   Error: {err}")
    sys.exit(1)
print("   Done")

# 3. Reboot
print("\n3. Rebooting VM 191 (required for new kernel to load)...")
print("   VM will come back in ~60–90 seconds.")
sudo("reboot")
print("\n=== VM 191 is rebooting ===")
print("Wait 1–2 minutes, then open Proxmox Console again. Mouse clicks should work.")
print("If not: try releasing mouse from console (click the release button) and re-attaching.")
ssh.close()
