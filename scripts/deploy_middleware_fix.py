import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output, exit_code

print("=" * 70)
print("DEPLOYING MIDDLEWARE FIX TO VM")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Read the fixed middleware file
with open(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\lib\supabase\middleware.ts', 'r', encoding='utf-8') as f:
    middleware_content = f.read()

# Website code is at /opt/mycosoft/website on VM
WEBSITE_PATH = '/opt/mycosoft/website'
MIDDLEWARE_PATH = f'{WEBSITE_PATH}/lib/supabase/middleware.ts'

print("\n[1] Uploading fixed middleware file to VM...")
sftp = ssh.open_sftp()
with sftp.file('/tmp/middleware.ts', 'w') as f:
    f.write(middleware_content)
sftp.close()

# Copy to website directory
print("\n[2] Copying file to website directory...")
run(ssh, f"echo '{VM_PASS}' | sudo -S cp /tmp/middleware.ts {MIDDLEWARE_PATH}")

# Rebuild Docker image with the fixed file
print("\n[3] Rebuilding Docker image (this may take 5-10 minutes)...")
run(ssh, f"cd {WEBSITE_PATH} && echo '{VM_PASS}' | sudo -S docker build -t website-website:latest --no-cache .", timeout=900)

# Restart container
print("\n[4] Restarting container...")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website")

time.sleep(5)

print("\n[5] Verifying container is running...")
run(ssh, "docker ps | grep mycosoft-website")

print("\n[6] Testing website...")
output, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
print(f"HTTP Status: {output.strip()}")

print("\n" + "=" * 70)
print("MIDDLEWARE FIX DEPLOYED!")
print("=" * 70)
print("\nNote: This fix is temporary (in container). For permanent fix, you need to:")
print("1. Push code to GitHub (when network is available)")
print("2. Rebuild Docker image: docker-compose build mycosoft-website --no-cache")

ssh.close()
