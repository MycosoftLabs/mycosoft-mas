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
    print("Connected to MINDEX VM!")
    
    # Check system info
    print("\n=== System Info ===")
    stdin, stdout, stderr = ssh.exec_command("uname -a && cat /etc/os-release | head -5 && df -h / && free -h")
    time.sleep(3)
    print(stdout.read().decode())
    
    # Check cloud-init status
    print("\n=== Cloud-init Status ===")
    stdin, stdout, stderr = ssh.exec_command("cloud-init status --wait 2>/dev/null || echo 'Cloud-init not ready'")
    time.sleep(5)
    print(stdout.read().decode())
    
    # Check IP
    print("\n=== Network ===")
    stdin, stdout, stderr = ssh.exec_command("ip addr show | grep -A2 'inet '")
    time.sleep(2)
    print(stdout.read().decode())
    
    ssh.close()
    print("\nSSH connection successful!")
    
except Exception as e:
    print(f"Error: {e}")
