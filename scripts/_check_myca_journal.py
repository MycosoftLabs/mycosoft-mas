"""Check MYCA OS journal and error log for the real exit reason."""
import paramiko, os, time
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

def run(cmd, timeout=15):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

def sudo_run(cmd, timeout=15):
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.get_pty()
    chan.exec_command(f"sudo -S bash -c '{cmd}'")
    chan.send(pw + "\n")
    time.sleep(2)
    out = b""
    try:
        while True:
            chunk = chan.recv(4096)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    chan.close()
    return out.decode(errors="replace")

# Check journal
print("=== SYSTEMD JOURNAL (myca-os) ===")
result = sudo_run("journalctl -u myca-os --no-pager -n 50 2>/dev/null")
for line in result.splitlines():
    if not line.startswith("[sudo]") and pw not in line:
        print(f"  {line}")

# Check error log
print("\n=== ERROR LOG ===")
out, _ = run("cat /opt/myca/logs/myca_os_error.log 2>/dev/null | tail -30")
print(out if out.strip() else "  (empty)")

# Check the service file
print("\n=== SERVICE FILE ===")
out, _ = run("cat /etc/systemd/system/myca-os.service 2>/dev/null")
print(out)

# Try running it manually to see the real error
print("\n=== MANUAL RUN TEST (5 sec) ===")
out, err = run("cd /home/mycosoft/repos/mycosoft-mas && timeout 5 python3 -m mycosoft_mas.myca.os 2>&1 | head -30", timeout=15)
print(out[:1500])
if err:
    print(f"STDERR: {err[:500]}")

ssh.close()
