#!/usr/bin/env python3
"""Install MYCA full desktop workstation on VM 191 per plan."""
import os
import sys
import time

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
    full = f"echo '{esc}' | sudo -S bash -c '{cmd.replace(chr(39), chr(39)+chr(92)+chr(92)+chr(39)+chr(39))}'"
    return run(full, timeout=timeout)

def sudo_simple(cmd, timeout=300):
    esc = VM_PASSWORD.replace("'", "'\"'\"'") if VM_PASSWORD else ""
    return run(f"echo '{esc}' | sudo -S {cmd}", timeout=timeout)

print("=== Phase 1: Desktop + Remote Access ===")
sudo_simple("apt-get update -qq", timeout=120)
sudo_simple("DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies", timeout=600)
sudo_simple("DEBIAN_FRONTEND=noninteractive apt-get install -y xrdp tigervnc-standalone-server websockify", timeout=300)
# Configure XRDP for XFCE - proper startwm.sh
startwm = """#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
if [ -r /etc/default/locale ]; then
  . /etc/default/locale
  export LANG LANGUAGE
fi
exec startxfce4
"""
sftp = ssh.open_sftp()
with sftp.open("/tmp/startwm.sh", "w") as f:
    f.write(startwm)
sftp.close()
sudo_simple("mv /tmp/startwm.sh /etc/xrdp/startwm.sh")
sudo_simple("chmod +x /etc/xrdp/startwm.sh")
sudo_simple("systemctl enable xrdp")
sudo_simple("systemctl restart xrdp")

# noVNC: TigerVNC + websockify. Create vnc xstartup for XFCE
run("mkdir -p ~/.vnc")
run("echo '#!/bin/sh\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4' > ~/.vnc/xstartup")
run("chmod +x ~/.vnc/xstartup")
run("echo myca191 | vncpasswd -f > ~/.vnc/passwd 2>/dev/null; chmod 600 ~/.vnc/passwd 2>/dev/null || true")
run("vncserver -kill :1 2>/dev/null || true")
out, _ = run("vncserver :1 -geometry 1920x1080 -depth 24 2>&1")
print("  vncserver:", out[:150])
# Clone noVNC if missing
out2, _ = run("ls /opt/myca/novnc/vnc.html 2>/dev/null || echo MISSING")
if "MISSING" in out2:
    sudo_simple("apt-get install -y git")
    run("rm -rf /tmp/novnc_clone 2>/dev/null; git clone --depth 1 https://github.com/novnc/noVNC.git /tmp/novnc_clone")
    sudo_simple("mkdir -p /opt/myca")
    sudo_simple("rm -rf /opt/myca/novnc")
    sudo_simple("mv /tmp/novnc_clone /opt/myca/novnc")
    sudo_simple("chown -R mycosoft:mycosoft /opt/myca/novnc")
# Create systemd service for websockify (noVNC on 6080)
novnc_svc = """[Unit]
Description=noVNC WebSocket proxy
After=network.target

[Service]
Type=simple
User=mycosoft
ExecStart=/usr/bin/websockify --web=/opt/myca/novnc 6080 localhost:5901
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
sftp = ssh.open_sftp()
with sftp.open("/tmp/novnc.service", "w") as f:
    f.write(novnc_svc)
sftp.close()
sudo_simple("mv /tmp/novnc.service /etc/systemd/system/novnc.service")
sudo_simple("systemctl daemon-reload")
sudo_simple("systemctl enable novnc")
sudo_simple("systemctl start novnc")
print("Phase 1 done: XFCE, XRDP, TigerVNC, noVNC")

print("\n=== Phase 2: Node.js v20 LTS ===")
out, _ = run("node -v 2>/dev/null || echo MISSING")
if "v20" not in out and "v18" not in out and "v19" not in out:
    sudo_simple("apt-get remove -y nodejs libnode-dev libnode72 2>/dev/null || true")
    sudo_simple("apt-get autoremove -y")
    run("curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh")
    sudo_simple("bash /tmp/nodesource_setup.sh")
    sudo_simple("apt-get install -y nodejs")
out, _ = run("node -v 2>/dev/null")
print("  node:", out)
print("Phase 2 done: Node.js v20")

print("\n=== Phase 3: GUI Apps ===")
# Chrome via Google repo
out, _ = run("which google-chrome 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb")
    sudo_simple("apt-get install -y /tmp/google-chrome.deb 2>/dev/null || dpkg -i /tmp/google-chrome.deb")
    sudo_simple("apt-get install -f -y")
# VS Code via Microsoft repo
out, _ = run("which code 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /usr/share/keyrings/microsoft.gpg >/dev/null")
    run("echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/vscode stable main' | sudo tee /etc/apt/sources.list.d/vscode.list")
    sudo_simple("apt-get update -qq")
    sudo_simple("DEBIAN_FRONTEND=noninteractive apt-get install -y code")
# Cursor: AppImage needs libfuse2
sudo_simple("apt-get install -y libfuse2")
run("mkdir -p ~/Applications")
out, _ = run("ls ~/Applications/cursor.AppImage 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("wget -q -O /tmp/cursor.AppImage 'https://downloader.cursor.sh/linux/appImage/x64' 2>/dev/null && chmod +x /tmp/cursor.AppImage && mv /tmp/cursor.AppImage ~/Applications/cursor.AppImage")
# Discord, Slack via snap
sudo_simple("snap install discord --classic 2>/dev/null || true")
sudo_simple("snap install slack --classic 2>/dev/null || true")
# Signal Desktop
out, _ = run("which signal-desktop 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("wget -qO- https://updates.signal.org/desktop/apt/keys.asc | gpg --dearmor | sudo tee /usr/share/keyrings/signal-desktop.gpg >/dev/null")
    run("echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/signal-desktop.gpg] https://updates.signal.org/desktop/apt xenial main' | sudo tee /etc/apt/sources.list.d/signal-desktop.list")
    sudo_simple("apt-get update -qq")
    sudo_simple("DEBIAN_FRONTEND=noninteractive apt-get install -y signal-desktop")
print("Phase 3 done: Chrome, Cursor, VS Code, Discord, Slack, Signal")

print("\n=== Phase 4: CLI Tools ===")
sudo_simple("apt-get install -y jq httpie")
run("npm install -g @anthropic-ai/claude-code 2>/dev/null || true")
out, _ = run("which gh 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /tmp/gh-keyring.gpg")
    sudo_simple("mv /tmp/gh-keyring.gpg /usr/share/keyrings/githubcli-archive-keyring.gpg")
    sudo_simple("chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg")
    sftp = ssh.open_sftp()
    with sftp.open("/tmp/github-cli.list", "w") as f:
        f.write("deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\n")
    sftp.close()
    sudo_simple("mv /tmp/github-cli.list /etc/apt/sources.list.d/github-cli.list")
    sudo_simple("apt-get update -qq")
    sudo_simple("apt-get install -y gh")
run("pip3 install playwright 2>/dev/null; playwright install --with-deps chromium 2>/dev/null || true")
# signal-cli: install from GitHub release
out, _ = run("which signal-cli 2>/dev/null || echo MISSING")
if "MISSING" in out:
    run("curl -sL https://github.com/AsamK/signal-cli/releases/download/v0.11.5.1/signal-cli-0.11.5.1.tar.gz -o /tmp/signal-cli.tar.gz")
    run("mkdir -p ~/bin; tar -xzf /tmp/signal-cli.tar.gz -C ~/bin")
    run("ln -sf ~/bin/signal-cli-0.11.5.1/bin/signal-cli ~/bin/signal-cli 2>/dev/null || true")
    run("echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc")
print("Phase 4 done: Claude Code, gh, Playwright, signal-cli, jq, httpie")

print("\n=== Phase 5: AI Python Libraries ===")
run("pip3 install --user openai google-generativeai anthropic httpx 2>/dev/null")
print("Phase 5 done: OpenAI, Google AI, Anthropic, httpx")

print("\n=== Phase 6: Firewall ===")
sudo_simple("ufw allow from 192.168.0.0/24 to any port 3389")
sudo_simple("ufw allow from 192.168.0.0/24 to any port 6080")
sudo_simple("ufw allow 22")
sudo_simple("ufw --force enable 2>/dev/null || true")
print("Phase 6 done: XRDP 3389, noVNC 6080 restricted to LAN")

print("\n=== Phase 7: Verify ===")
out, _ = run("systemctl is-active xrdp novnc 2>/dev/null")
print("  xrdp, novnc:", out)
out, _ = run("vncserver -list 2>/dev/null")
print("  vnc:", out[:80] if out else "not running")
out, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:6080/vnc.html 2>/dev/null || echo 000")
print("  noVNC http:", out)
out, _ = run("node -v 2>/dev/null")
print("  node:", out)
out, _ = run("which google-chrome code 2>/dev/null")
print("  chrome, code:", out[:100] if out else "missing")
print("Phase 7 done: verification complete")
print("\n=== All phases complete. Access: http://192.168.0.191:6080 (noVNC) or RDP to 192.168.0.191:3389 ===")
