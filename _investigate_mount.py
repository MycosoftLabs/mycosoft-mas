import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sandbox_host = "192.168.0.187"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Investigating working mount on Sandbox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(sandbox_host, username=user, password=passwd, timeout=15)

# Check how the mount actually works
print("=== Active CIFS sessions ===")
stdin, stdout, stderr = ssh.exec_command("sudo cat /proc/fs/cifs/DebugData 2>/dev/null | head -50 || echo 'No debug data'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Check keyring
print("=== Keyring ===")
stdin, stdout, stderr = ssh.exec_command("keyctl show @u 2>/dev/null || echo 'No keyring'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Create the credentials file that's missing
print("=== Creating credentials file ===")
# Ask for the NAS password from the user by mounting info
stdin, stdout, stderr = ssh.exec_command("mount | grep mycosoft.com | head -1")
time.sleep(2)
mount_line = stdout.read().decode('utf-8', errors='replace')
print(f"Mount: {mount_line}")

# Check what systemd mount unit uses
print("=== Systemd mount units ===")
stdin, stdout, stderr = ssh.exec_command("systemctl list-units --type=mount | grep -i nas; sudo systemctl status mnt-mycosoft*.mount 2>/dev/null || echo 'checking'")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
