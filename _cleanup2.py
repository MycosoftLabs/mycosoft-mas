import paramiko
import time

wrong_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Using pvesh to stop VM on {wrong_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(wrong_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Get the PID and kill it, then immediately destroy
cmd = '''
# Find and kill the qemu process
PID=$(pgrep -f "kvm.*105")
if [ ! -z "$PID" ]; then
    echo "Killing PID: $PID"
    kill -9 $PID
    sleep 3
fi

# Remove any locks
rm -f /var/lock/qemu-server/lock-105.conf
rm -f /run/lock/qemu-server/lock-105.conf

# Wait a moment
sleep 2

# Check status
qm status 105 2>&1

# Try destroy
qm destroy 105 --purge 2>&1

# List VMs
qm list
'''

print("\n=== Executing cleanup ===")
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(15)
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
