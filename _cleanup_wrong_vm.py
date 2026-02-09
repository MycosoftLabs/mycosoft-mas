import paramiko
import time

# Delete VM from wrong Proxmox (192.168.0.90)
wrong_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Cleaning up VM from wrong Proxmox ({wrong_host})...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(wrong_host, username=proxmox_user, password=proxmox_pass, timeout=15)
    print("Connected!")
    
    # Stop and delete VM 105
    print("\n=== Stopping and deleting VM 105 ===")
    stdin, stdout, stderr = ssh.exec_command("qm stop 105 --timeout 30; qm destroy 105 --purge")
    time.sleep(15)
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Verify deleted
    stdin, stdout, stderr = ssh.exec_command("qm list")
    time.sleep(2)
    print("Remaining VMs:", stdout.read().decode())
    
    ssh.close()
    print("Cleanup complete!")
    
except Exception as e:
    print(f"Error: {e}")
