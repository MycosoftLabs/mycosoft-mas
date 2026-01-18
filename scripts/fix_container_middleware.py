import paramiko
import sys
import time
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
print("FIXING MIDDLEWARE IN CONTAINER")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Find where middleware actually is in container
print("\n[1] Finding middleware file in container...")
run(ssh, "docker exec mycosoft-website find /app -name 'middleware.ts' -type f 2>/dev/null")
run(ssh, "docker exec mycosoft-website find /app -path '*/lib/supabase/middleware.ts' -type f 2>/dev/null")

# Check if lib/supabase exists
print("\n[2] Checking lib/supabase directory...")
run(ssh, "docker exec mycosoft-website ls -la /app/lib/supabase/ 2>/dev/null || echo 'Directory does not exist'")

# Check what's in .next/server for middleware
print("\n[3] Checking .next/server for middleware...")
run(ssh, "docker exec mycosoft-website find /app/.next -name '*middleware*' -type f 2>/dev/null | head -5")

# Read the middleware file from VM
print("\n[4] Reading middleware file from VM source...")
output, _ = run(ssh, "cat /opt/mycosoft/website/lib/supabase/middleware.ts | grep -A 5 'url.pathname =' | head -10")

# The issue is likely that the middleware was changed but not rebuilt in the container
# Let's copy it directly and rebuild
print("\n[5] Copying fixed middleware into container...")
run(ssh, "docker cp /opt/mycosoft/website/lib/supabase/middleware.ts mycosoft-website:/app/lib/supabase/middleware.ts 2>/dev/null || echo 'Failed to copy'")

# Restart container to see if it picks up changes
print("\n[6] Restarting container...")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production restart mycosoft-website")

time.sleep(5)

# Test redirect again
print("\n[7] Testing redirect after restart...")
output, _ = run(ssh, "curl -s -L -o /dev/null -w '%{url_effective}' -H 'Cookie: ' http://localhost:3000/dashboard/crep")
print(f"Redirected to: {output.strip()}")

print("\n" + "=" * 70)
print("NOTE: Middleware changes require Docker rebuild, not just file copy!")
print("=" * 70)
print("\nThe middleware file was copied, but Next.js middleware is compiled.")
print("To permanently fix, rebuild the Docker image:")
print("  cd /opt/mycosoft/website")
print("  docker build -t website-website:latest --no-cache .")

ssh.close()
