import paramiko
import time
import sys

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print(f"Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Verify Docker
print("\n=== Verifying Docker ===")
stdin, stdout, stderr = ssh.exec_command("sudo docker --version && sudo docker-compose --version")
time.sleep(3)
out = stdout.read().decode('utf-8', errors='replace')
print(out)

# Check Docker is running
print("\n=== Docker status ===")
stdin, stdout, stderr = ssh.exec_command("sudo systemctl is-active docker")
time.sleep(2)
status = stdout.read().decode().strip()
print(f"Docker service: {status}")

# Create directories
print("\n=== Creating directories ===")
stdin, stdout, stderr = ssh.exec_command("sudo mkdir -p /opt/mycosoft/ledger /opt/mycosoft/mindex /opt/mycosoft/data && sudo chown -R mycosoft:mycosoft /opt/mycosoft && ls -la /opt/mycosoft/")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Test Docker
print("\n=== Testing Docker ===")
stdin, stdout, stderr = ssh.exec_command("sudo docker run --rm hello-world 2>&1 | head -5")
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Docker verified!")
