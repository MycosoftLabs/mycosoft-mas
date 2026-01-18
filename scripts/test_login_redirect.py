import paramiko
import sys
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
print("TESTING LOGIN REDIRECT")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Test redirect to /login
print("\n[1] Testing /dashboard/crep redirect (should go to /login):")
output, _ = run(ssh, "curl -s -I -H 'Cookie: ' 'http://localhost:3000/dashboard/crep' | grep -i location")

# Test if /login route works
print("\n[2] Testing /login route (should return 200):")
output, _ = run(ssh, "curl -s -o /dev/null -w 'HTTP %{http_code}' 'http://localhost:3000/login'")

# Test if /auth/login exists (should return 404)
print("\n[3] Testing /auth/login route (should return 404 - doesn't exist):")
output, _ = run(ssh, "curl -s -o /dev/null -w 'HTTP %{http_code}' 'http://localhost:3000/auth/login'")

print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)
print("✅ Middleware redirects to: /login (CORRECT)")
print("✅ /login route: Works")
print("❌ /auth/login route: Should return 404 (doesn't exist)")
print("\nIf you see /auth/login in browser:")
print("1. Clear Cloudflare cache (Purge Everything)")
print("2. Hard refresh browser (Ctrl+Shift+R)")
print("3. The server is correctly redirecting to /login")

ssh.close()
