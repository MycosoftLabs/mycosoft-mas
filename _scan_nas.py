import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Connect to MINDEX VM to configure NAS
mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print("Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Install CIFS and scan NAS shares
print("\n=== Installing CIFS and scanning NAS ===")
cmd = '''
# Install CIFS utils
sudo apt-get update -qq
sudo apt-get install -y -qq cifs-utils smbclient

# Scan NAS for shares
echo "=== Scanning NAS shares at 192.168.0.105 ==="
smbclient -L //192.168.0.105 -N 2>/dev/null || echo "Anonymous access denied, trying with credentials..."
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(30)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err and "error" in err.lower():
    print(err)

ssh.close()
print("Done!")
