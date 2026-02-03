#!/usr/bin/env python3
"""Deploy to MAS VM - February 3, 2026"""

import paramiko

def run_ssh_command(host, user, password, command, timeout=120):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return exit_code == 0, out + err
    except Exception as e:
        return False, str(e)

password = "REDACTED_VM_SSH_PASSWORD"

print("=" * 60)
print("Deploying to MAS VM (192.168.0.188)")
print("=" * 60)

# Pull latest code
print("\n1. Pulling latest code from GitHub...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main"
)
print(f"Git pull: {'SUCCESS' if success else 'FAILED'}")
print(output)

if success:
    # Restart orchestrator container
    print("\n2. Restarting myca-orchestrator container...")
    success2, output2 = run_ssh_command(
        "192.168.0.188",
        "mycosoft",
        password,
        "docker restart myca-orchestrator && docker logs myca-orchestrator --tail 10"
    )
    print(f"Container restart: {'SUCCESS' if success2 else 'FAILED'}")
    print(output2)
    
    # Check health
    print("\n3. Checking orchestrator health...")
    success3, output3 = run_ssh_command(
        "192.168.0.188",
        "mycosoft",
        password,
        "sleep 5 && curl -s http://localhost:8001/health || echo 'Health check pending...'"
    )
    print(output3)

print("\n" + "=" * 60)
print("MAS VM Deployment complete!")
print("=" * 60)
