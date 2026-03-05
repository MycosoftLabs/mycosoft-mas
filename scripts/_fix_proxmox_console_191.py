#!/usr/bin/env python3
"""Fix Proxmox console on VM 191: install LightDM so primary display (:0) shows desktop.

Proxmox's built-in Console connects to the VM's primary display. Without a display
manager on :0, you see a black screen. This installs LightDM + autologin so the
desktop appears in Proxmox Console.

After running: Proxmox Console will show XFCE. You can also keep using:
  - noVNC: http://192.168.0.191:6080
  - RDP: 192.168.0.191:3389
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

print("=== Fix Proxmox Console on VM 191 ===\n")

# 1. Install LightDM
print("1. Installing LightDM...")
sudo("DEBIAN_FRONTEND=noninteractive apt-get update -qq && apt-get install -y lightdm")
print("   Done")

# 2. Configure LightDM for XFCE + autologin
print("2. Configuring LightDM (autologin, XFCE)...")
lightdm_conf = """[Seat:*]
user-session=xfce
autologin-user=mycosoft
autologin-user-timeout=0
"""
sudo("mkdir -p /etc/lightdm/lightdm.conf.d")
sftp = ssh.open_sftp()
with sftp.open("/tmp/lightdm.conf", "w") as f:
    f.write(lightdm_conf)
sftp.close()
sudo("cp /tmp/lightdm.conf /etc/lightdm/lightdm.conf.d/50-myca-autologin.conf")
print("   Done")

# 3. Set LightDM as default display manager
print("3. Setting LightDM as default DM...")
sudo("echo /usr/sbin/lightdm | debconf-set-selections")
sudo("DEBIAN_FRONTEND=noninteractive dpkg-reconfigure lightdm 2>/dev/null || true")
print("   Done")

# 4. Reboot (or restart lightdm if already running)
print("4. Restarting display manager...")
out, err = sudo("systemctl restart lightdm 2>&1")
if "failed" in (out + err).lower():
    print("   LightDM may need reboot. Reboot VM 191? Run: ssh mycosoft@192.168.0.191 'sudo reboot'")
else:
    print("   LightDM restarted")
print("\n=== Proxmox Console should now show desktop ===")
print("If still black: reboot VM 191 and try Proxmox Console again.")
print("Alternative: http://192.168.0.191:6080 (noVNC) or RDP 192.168.0.191:3389")
