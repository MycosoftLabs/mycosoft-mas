import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "REDACTED_VM_SSH_PASSWORD"

print(f"Connecting to MINDEX VM at {mindex_host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
    print("Connected!")
    
    # Check system
    stdin, stdout, stderr = ssh.exec_command("uname -a && hostname && ip addr show eth0 | grep 'inet '")
    time.sleep(3)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Wait for cloud-init
    print("\n=== Waiting for cloud-init ===")
    stdin, stdout, stderr = ssh.exec_command("cloud-init status --wait 2>/dev/null; echo 'Cloud-init done'")
    time.sleep(30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    ssh.close()
    print("SSH successful!")
    
except Exception as e:
    print(f"Error: {e}")
