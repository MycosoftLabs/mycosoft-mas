import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print(f"Connecting to MINDEX VM at {mindex_host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
    print("Connected!")
    
    # Check system
    stdin, stdout, stderr = ssh.exec_command("hostname && uname -a")
    time.sleep(2)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Check Docker
    print("\n=== Docker status ===")
    stdin, stdout, stderr = ssh.exec_command("sudo docker --version 2>&1 && sudo systemctl is-active docker 2>&1")
    time.sleep(3)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Check cloud-init status
    print("\n=== Cloud-init status ===")
    stdin, stdout, stderr = ssh.exec_command("cloud-init status 2>&1")
    time.sleep(2)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    ssh.close()
    print("SSH successful!")
    
except Exception as e:
    print(f"Error: {e}")
