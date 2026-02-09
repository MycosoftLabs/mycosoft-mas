import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print("Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Start containers
print("\n=== Starting MINDEX containers ===")
cmd = '''cd /opt/mycosoft/mindex && sudo docker-compose up -d 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(60)  # Wait for containers to start
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(err)

# Check containers
print("\n=== Container status ===")
stdin, stdout, stderr = ssh.exec_command("sudo docker ps")
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check ports
print("\n=== Listening ports ===")
stdin, stdout, stderr = ssh.exec_command("sudo ss -tlnp | grep -E '5432|6379|6333'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Containers started!")
