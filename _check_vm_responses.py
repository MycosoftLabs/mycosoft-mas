"""Check the actual response patterns in VM code."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Checking VM response patterns...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

def run_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check for Mycosoft pattern in the file
print("Checking for 'Mycosoft is pioneering' text...")
result = run_command("grep 'Mycosoft is pioneering' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"Result: {result[:200] if result else 'NOT FOUND'}")

# Check the science patterns
print("\nChecking for science pattern text...")
result = run_command("grep 'biological intelligence' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"Result: {result[:200] if result else 'NOT FOUND'}")

# Get the full method with context
print("\nGetting response patterns section...")
result = run_command("grep -A 3 'mycosoft_patterns' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"Result:\n{result[:500] if result else 'NOT FOUND'}")

# Check if old fallback patterns exist
print("\nChecking for 'limited mode' text...")
result = run_command("grep -c 'limited mode' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"Count: {result}")

ssh.close()
print("\nDone!")
