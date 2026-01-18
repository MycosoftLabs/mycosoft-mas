import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print("=" * 70)
print("CLEANING UP VM DISK SPACE")
print("=" * 70)

print("\n[1] Before cleanup:")
run(ssh, "df -h /")

print("\n[2] Clearing Docker build cache (10+ GB)...")
run(ssh, f'echo "{VM_PASS}" | sudo -S docker builder prune -af')

print("\n[3] Removing unused Docker images...")
run(ssh, f'echo "{VM_PASS}" | sudo -S docker image prune -f')

print("\n[4] Removing stopped containers...")
run(ssh, f'echo "{VM_PASS}" | sudo -S docker container prune -f')

print("\n[5] Cleaning apt cache...")
run(ssh, f'echo "{VM_PASS}" | sudo -S apt-get clean')
run(ssh, f'echo "{VM_PASS}" | sudo -S apt-get autoremove -y')

print("\n[6] Cleaning journal logs (keeping 100MB)...")
run(ssh, f'echo "{VM_PASS}" | sudo -S journalctl --vacuum-size=100M')

print("\n[7] Removing old snap versions...")
run(ssh, f'echo "{VM_PASS}" | sudo -S snap list --all | awk "/disabled/{{print \$1, \$3}}" | while read snapname revision; do sudo snap remove "$snapname" --revision="$revision"; done 2>/dev/null || true')

print("\n[8] After cleanup:")
run(ssh, "df -h /")

print("\n[9] Docker space now:")
run(ssh, "docker system df")

ssh.close()
print("\n" + "=" * 70)
print("CLEANUP COMPLETE")
print("=" * 70)
