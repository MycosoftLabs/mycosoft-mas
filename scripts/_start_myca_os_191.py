"""Start MYCA OS on VM 191 -- handles sudo with password."""
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

def run(cmd, timeout=30, use_sudo=False):
    if use_sudo:
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
    else:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        return stdout.read().decode() + stderr.read().decode()

# Step 1: Install service file
print("Installing myca-os systemd service...")
result = run("cp /tmp/myca-os.service /etc/systemd/system/myca-os.service 2>/dev/null; systemctl daemon-reload; echo DONE", use_sudo=True)
print(f"  {result.strip()[-50:]}")

# Step 2: Enable and start
print("Enabling and starting myca-os...")
result = run("systemctl enable myca-os; systemctl start myca-os; echo STARTED", use_sudo=True)
print(f"  {result.strip()[-100:]}")

time.sleep(5)

# Step 3: Check status
print("\nChecking myca-os status...")
result = run("systemctl is-active myca-os")
print(f"  Status: {result.strip()}")

# Step 4: Check logs
print("\nRecent logs:")
result = run("tail -30 /opt/myca/logs/myca_os.log 2>/dev/null")
log_text = result.strip()
if log_text:
    for line in log_text.splitlines()[-15:]:
        print(f"  {line}")
else:
    print("  No log output yet")
    result = run("journalctl -u myca-os --no-pager -n 20 2>/dev/null", use_sudo=True)
    for line in result.strip().splitlines()[-10:]:
        print(f"  {line}")

# Step 5: Show all services
print("\n\nAll Docker containers on 191:")
result = run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
print(result.strip())

# Step 6: Port check
print("\nPort status:")
for port, name in [(22, "SSH"), (5679, "n8n"), (8089, "Signal"), (8100, "Workspace API"), (5433, "Postgres")]:
    try:
        s = socket.create_connection(("192.168.0.191", port), 3)
        s.close()
        print(f"  {name:20s} :{port}  OPEN")
    except:
        print(f"  {name:20s} :{port}  CLOSED")

ssh.close()
print("\nDone.")
