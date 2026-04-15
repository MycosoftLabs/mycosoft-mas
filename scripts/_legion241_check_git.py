from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)
for cmd in [
    r'cmd.exe /c if exist C:\Users\owner1\mycosoft-mas\.git echo HAS_GIT else echo NO_GIT',
    r'cmd.exe /c where git',
    r'cmd.exe /c where git-lfs',
]:
    _, o, e = c.exec_command(cmd, timeout=25)
    print(cmd, "->", (o.read() + e.read()).decode(errors="replace").strip())
c.close()
