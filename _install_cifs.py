import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Installing CIFS utilities on MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Install cifs-utils
install_cmd = '''
sudo apt-get update -qq
sudo apt-get install -y cifs-utils keyutils
sudo modprobe cifs
lsmod | grep cifs
'''
stdin, stdout, stderr = ssh.exec_command(install_cmd)
time.sleep(60)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

# Now try mounting
print("\n=== Attempting mount ===")
mount_cmd = '''
sudo mount -a
sleep 2
mount | grep cifs
ls -la /mnt/mycosoft-nas/
'''
stdin, stdout, stderr = ssh.exec_command(mount_cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
