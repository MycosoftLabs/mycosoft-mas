import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output, exit_code

print("=" * 70)
print("FINDING LOGIN PAGE LOCATION")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Check all possible login page locations
print("\n[1] Searching for login page in container:")
run(ssh, "docker exec mycosoft-website find /app -name '*login*' -type f 2>/dev/null | head -10")

# Check app directory structure
print("\n[2] App directory structure:")
run(ssh, "docker exec mycosoft-website ls -la /app/app/ 2>/dev/null | head -20")

# Check if login is in a different location
print("\n[3] Looking for login in source (VM):")
run(ssh, "find /opt/mycosoft/website/app -name '*login*' -type f 2>/dev/null | head -5")

# Test if /login route works
print("\n[4] Testing /login route (HTTP status):")
output, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/login")
print(f"HTTP Status: {output.strip()}")

# Check what happens when accessing /login
print("\n[5] Full response from /login:")
run(ssh, "curl -s 'http://localhost:3000/login' | head -20")

ssh.close()
