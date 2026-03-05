"""Pull latest code on VM 191 and restart MYCA OS."""
import paramiko, os, time, socket
from pathlib import Path

def load_creds():
    cf = Path(__file__).parent.parent / ".credentials.local"
    if cf.exists():
        for line in cf.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_creds()
pw = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD", ""))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)

def run(cmd, timeout=30):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

def sudo_run(cmd, timeout=30):
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.get_pty()
    chan.exec_command(f"sudo -S bash -c '{cmd}'")
    chan.send(pw + "\n")
    time.sleep(2)
    out = b""
    while chan.recv_ready():
        out += chan.recv(4096)
    time.sleep(1)
    while chan.recv_ready():
        out += chan.recv(4096)
    chan.close()
    return out.decode(errors="replace")

# 1. Pull latest code
print("Pulling latest code on 191...")
out, err = run("cd /home/mycosoft/repos/mycosoft-mas && git pull origin main 2>&1 | tail -5", timeout=30)
print(f"  {out.strip()}")

# 2. Restart MYCA OS
print("\nRestarting MYCA OS daemon...")
result = sudo_run("systemctl restart myca-os")
print(f"  {result.strip()[-80:]}")

time.sleep(8)

# 3. Check status
out, _ = run("systemctl is-active myca-os 2>/dev/null")
status = out.strip()
print(f"\n  myca-os status: {status}")

# 4. Check logs
print("\nRecent logs:")
out, _ = run("tail -25 /opt/myca/logs/myca_os.log 2>/dev/null")
if out.strip():
    for line in out.strip().splitlines()[-15:]:
        print(f"  {line}")
else:
    print("  No log file. Checking journal...")
    result = sudo_run("journalctl -u myca-os --no-pager -n 20 2>/dev/null")
    for line in result.strip().splitlines()[-15:]:
        if not line.startswith("[sudo]"):
            print(f"  {line}")

# 5. Port check
print("\nPort status:")
for port, name in [(22, "SSH"), (5679, "n8n"), (8089, "Signal"), (8100, "Workspace"), (5433, "Postgres")]:
    try:
        s = socket.create_connection(("192.168.0.191", port), 3)
        s.close()
        print(f"  {name:20s} :{port}  OPEN")
    except:
        print(f"  {name:20s} :{port}  CLOSED")

# 6. Docker containers
print("\nDocker containers:")
out, _ = run("docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null")
print(out.strip())

ssh.close()
print("\nDone.")
