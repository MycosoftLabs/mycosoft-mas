"""One-off: pull and restart MAS on VM 188."""
import os
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = ""
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                pw = v.strip()
                break

pw = pw or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

o, e = run("cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main")
print("Pull:", o[:300] if o else "ok", e[:200] if e else "")

# sudo with password via stdin
sin, sout, serr = client.exec_command("sudo -S systemctl restart mas-orchestrator")
sin.write(pw + "\n")
sin.flush()
sin.channel.shutdown_write()
out = sout.read().decode()
err = serr.read().decode()
print("Restart:", "ok" if not err else err[:200])

client.close()
print("Deploy done.")
