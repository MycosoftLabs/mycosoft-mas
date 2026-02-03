"""Verify the VM has the latest code with enhanced responses."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Checking VM code version...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check git log
git_log = run_command("cd /home/mycosoft/mycosoft/mas && git log -1 --oneline")
print(f"Git log: {git_log}")

# Check if the enhanced responses are in the file
check_mycosoft = run_command("grep -c 'mycosoft_patterns' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"mycosoft_patterns in file: {check_mycosoft}")

check_science = run_command("grep -c 'science_patterns' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py")
print(f"science_patterns in file: {check_science}")

# Check first few lines of _generate_local_response
check_method = run_command("grep -A 5 '_generate_local_response' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/voice_orchestrator_api.py | head -10")
print(f"Method content:\n{check_method}")

# Force restart the container
print("\nForce restarting container...")
restart_result = run_command("docker restart myca-orchestrator")
print(f"Restart: {restart_result}")

import time
time.sleep(20)

# Check container logs
logs = run_command("docker logs myca-orchestrator --tail 10 2>&1")
print(f"\nContainer logs:\n{logs}")

ssh.close()
print("Done!")
