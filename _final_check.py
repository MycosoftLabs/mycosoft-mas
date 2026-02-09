import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "REDACTED_VM_SSH_PASSWORD"

print("Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Set up ledger file
print("\n=== Setting up ledger file ===")
cmd = '''
# Create ledger file
touch /opt/mycosoft/ledger/chain.jsonl
chmod 644 /opt/mycosoft/ledger/chain.jsonl

# Initialize with genesis entry
cat > /opt/mycosoft/ledger/chain.jsonl << 'EOF'
{"record_type":"block","block_number":0,"previous_hash":"0000000000000000000000000000000000000000000000000000000000000000","timestamp":"2026-02-04T00:00:00Z","description":"Genesis block"}
EOF

cat /opt/mycosoft/ledger/chain.jsonl
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Final system check
print("\n=== Final System Check ===")
cmd = '''
echo "=== Hostname ==="
hostname

echo -e "\\n=== IP Address ==="
ip addr show | grep "inet " | grep -v 127.0.0.1

echo -e "\\n=== Disk Usage ==="
df -h /

echo -e "\\n=== Memory Usage ==="
free -h

echo -e "\\n=== Docker Containers ==="
sudo docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"

echo -e "\\n=== Services Listening ==="
sudo ss -tlnp | grep -E "LISTEN.*docker"
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("MINDEX VM setup complete!")
