#!/usr/bin/env python3
"""
Fix VM 191 so Proxmox console shows XFCE desktop instead of text terminal.
MYCA must have a visible desktop (apps, browser) with terminal in background.
Installs LightDM, sets graphical boot, auto-login for mycosoft.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file, encoding="utf-8").read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()
                break

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
use_key = os.path.exists(KEY_PATH)
if use_key:
    pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    ssh.connect(VM_IP, username=VM_USER, pkey=pkey, timeout=20)
else:
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=20)


def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err


def sudo(cmd, timeout=300):
    esc = VM_PASSWORD.replace("'", "'\"'\"'") if VM_PASSWORD else ""
    safe = cmd.replace(chr(39), chr(39) + chr(92) + chr(92) + chr(39) + chr(39))
    full = f"echo '{esc}' | sudo -S bash -c '{safe}'"
    return run(full, timeout=timeout)


def sudo_simple(cmd, timeout=300):
    esc = VM_PASSWORD.replace("'", "'\"'\"'") if VM_PASSWORD else ""
    return run(f"echo '{esc}' | sudo -S {cmd}", timeout=timeout)


print("=== Fix VM 191: Proxmox console shows XFCE desktop ===\n")

# 1. Install LightDM (display manager) if not present
print("1. Install LightDM display manager...")
out, err = sudo_simple("DEBIAN_FRONTEND=noninteractive apt-get install -y lightdm lightdm-gtk-greeter", timeout=120)
if err and "Unable to locate" not in err:
    print("  stderr:", err[:200])
print("  done")

# 2. Configure LightDM: XFCE default session
print("2. Set XFCE as default session...")
lightdm_conf = """[Seat:*]
user-session=xfce
autologin-user=mycosoft
autologin-user-timeout=0
"""
sftp = ssh.open_sftp()
with sftp.open("/tmp/lightdm.conf.d_50-myca.conf", "w") as f:
    f.write(lightdm_conf)
sftp.close()
sudo_simple("mkdir -p /etc/lightdm/lightdm.conf.d")
sudo_simple("mv /tmp/lightdm.conf.d_50-myca.conf /etc/lightdm/lightdm.conf.d/50-myca.conf")
sudo_simple("chmod 644 /etc/lightdm/lightdm.conf.d/50-myca.conf")
print("  done")

# 3. Set default boot target to graphical
print("3. Set default boot to graphical.target...")
sudo_simple("systemctl set-default graphical.target")
out, _ = run("systemctl get-default")
print("  default target:", out)

# 4. Enable lightdm (will start at next boot; start now if no X)
print("4. Enable LightDM...")
sudo_simple("systemctl enable lightdm")

# 5. Ensure mycosoft has .xsession or xfce4-session as default
run("mkdir -p ~/.config/autostart")
# Autostart xfce4-session if not already default
run("echo 'exec startxfce4' > ~/.xsession 2>/dev/null; chmod +x ~/.xsession 2>/dev/null || true")

# 6. If currently on multi-user, switch to graphical now (requires reboot for console to show desktop)
out, _ = run("systemctl isolate graphical.target 2>&1")
print("  isolated graphical target")

# 7. Ensure DISPLAY=:0 is set for user session (for MYCA daemon)
# MYCA OS / tool_orchestrator should use DISPLAY=:0 when running browser
run("grep -q 'export DISPLAY=:0' ~/.bashrc || echo 'export DISPLAY=:0' >> ~/.bashrc")
run("grep -q 'export DISPLAY=:0' ~/.profile || echo 'export DISPLAY=:0' >> ~/.profile")
print("5. DISPLAY=:0 in profile for MYCA apps")

print("\n=== Fix complete ===")
if "--reboot" in sys.argv:
    print("Rebooting VM now...")
    sudo_simple("reboot")
    print("VM is rebooting. Proxmox console will show XFCE desktop after boot.")
else:
    print("REBOOT the VM for Proxmox console to show desktop:")
    print("  python _fix_myca_191_console_desktop.py --reboot")
    print("  or: ssh mycosoft@192.168.0.191 'sudo reboot'")
print("\nAfter reboot:")
print("  - Proxmox console (VNC) -> XFCE desktop, auto-logged in as mycosoft")
print("  - noVNC http://192.168.0.191:6080 -> still works (TigerVNC :1)")
print("  - RDP 192.168.0.191:3389 -> still works")
print("\nMYCA daemon should run with DISPLAY=:0 so apps use the visible desktop.")
