"""Check myca_main.py fallback responses."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Checking myca_main.py fallback responses...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

def run_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check for 'limited mode' in myca_main.py
print("Checking myca_main.py for 'limited mode'...")
result = run_command("grep -n 'limited mode' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py")
print(f"Result: {result[:500] if result else 'NOT FOUND'}")

# Check for generate_myca_fallback_response function
print("\nChecking for generate_myca_fallback_response function...")
result = run_command("grep -A 20 'def generate_myca_fallback_response' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py | head -30")
print(f"Result:\n{result}")

# Check which fallback is being called
print("\nChecking which fallback is called for voice...")
result = run_command("grep -B 5 -A 5 'fallback' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py | head -30")
print(f"Result:\n{result}")

ssh.close()
print("\nDone!")
