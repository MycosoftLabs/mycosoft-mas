import paramiko
import sys
import base64
import json
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

# Decode the tunnel token to see what it contains
token = "eyJhIjoiYzMwZmFmODdhZmYxNGE5YTc1YWQ5ZWZhNWE0MzJmMzciLCJ0IjoiYmQzODUzMTMtYTQ0YS00N2FlLThmOGEtNTgxNjA4MTE4MTI3IiwicyI6IlpEUTJNbVl6TWpFdE9ERTBOeTAwWlRJeExUaGpaV010WXpJNU5tUXpNMlV6TVRoaiJ9"
try:
    decoded = base64.b64decode(token).decode('utf-8')
    token_data = json.loads(decoded)
    print("=== TUNNEL TOKEN INFO ===")
    print(f"Account ID: {token_data.get('a', 'N/A')}")
    print(f"Tunnel ID: {token_data.get('t', 'N/A')}")
    print(f"Secret (first 10 chars): {token_data.get('s', 'N/A')[:10]}...")
except Exception as e:
    print(f"Error decoding token: {e}")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('\n=== TUNNEL CONFIGURATION FROM LOGS ===')
_, out, _ = ssh.exec_command('journalctl -u cloudflared 2>&1 | grep "Updated to new configuration" | tail -1')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CHECK CLOUDFLARED VERSION ===')
_, out, _ = ssh.exec_command('cloudflared --version')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== TUNNEL CONNECTIONS ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics | grep "tunnel_server_locations"')
print(out.read().decode('utf-8', errors='replace'))

print('\n=== CURRENT REQUESTS COUNTER ===')
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:20241/metrics | grep "tunnel_total_requests"')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
