import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

vms = [
    ("MAS VM", "192.168.0.188"),
    ("Website Sandbox", "192.168.0.187"),
    ("MINDEX VM", "192.168.0.189"),
]

user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

results = []

for name, ip in vms:
    print(f"\n=== {name} ({ip}) ===")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=passwd, timeout=15)
        
        # Get system stats
        cmd = '''
echo "=== CPU/Memory/Disk ==="
echo "CPU Cores: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
echo ""
echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -15 || echo "No docker"
echo ""
echo "=== Top 5 CPU Processes ==="
ps aux --sort=-%cpu | head -6 | awk '{print $11, $3"%"}'
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        time.sleep(5)
        print(stdout.read().decode('utf-8', errors='replace'))
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")

print("\n=== VM Status Check Complete ===")
