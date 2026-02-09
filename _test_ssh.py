import paramiko
import time

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
    stdin, stdout, stderr = ssh.exec_command("uname -a")
    print(stdout.read().decode())
    
    ssh.close()
    
except paramiko.ssh_exception.AuthenticationException as e:
    print(f"Auth error: {e}")
    print("\nTrying via Proxmox console to enable password auth...")
except Exception as e:
    print(f"Error: {e}")
