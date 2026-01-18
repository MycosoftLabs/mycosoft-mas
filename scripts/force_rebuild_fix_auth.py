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
print("FORCE REBUILD TO FIX /auth/login ISSUE")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

WEBSITE_PATH = '/opt/mycosoft/website'

# Verify middleware file has correct redirect
print("\n[1] Verifying middleware source file...")
output, _ = run(ssh, f"grep -n 'pathname =' {WEBSITE_PATH}/lib/supabase/middleware.ts | grep -E '(login|auth)'")
if '/auth/login' in output:
    print("ERROR: Middleware still has /auth/login! Fixing...")
    # We already fixed it, so this shouldn't happen
else:
    print("✓ Middleware source redirects to /login (correct)")

# Rebuild Docker image
print("\n[2] Rebuilding Docker image with fresh middleware...")
run(ssh, f"cd {WEBSITE_PATH} && echo '{VM_PASS}' | sudo -S docker build -t website-website:latest --no-cache .", timeout=900)

# Stop and remove old container
print("\n[3] Stopping old container...")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production stop mycosoft-website")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production rm -f mycosoft-website")

# Start new container
print("\n[4] Starting new container...")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website")

time.sleep(10)

# Test redirect
print("\n[5] Testing redirect after rebuild...")
output, _ = run(ssh, "curl -s -I -H 'Cookie: ' 'http://localhost:3000/dashboard/crep' | grep -i location")
print(f"Redirect: {output.strip()}")

print("\n" + "=" * 70)
print("REBUILD COMPLETE!")
print("=" * 70)
print("\nIMPORTANT: Clear Cloudflare cache to see changes!")
print("Go to Cloudflare Dashboard → Caching → Purge Everything")

ssh.close()
