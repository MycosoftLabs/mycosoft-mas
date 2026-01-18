import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=120):
    print(f'\n{"="*60}')
    print(f'$ {cmd}')
    print("="*60)
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    return output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print("=" * 70)
print("FULL VM DISK SPACE AUDIT")
print("=" * 70)

# 1. Overall disk usage
run(ssh, 'df -h')

# 2. Top-level directories by size
run(ssh, f'echo "{VM_PASS}" | sudo -S du -h --max-depth=1 / 2>/dev/null | sort -hr | head -20')

# 3. Docker specific usage
run(ssh, 'docker system df -v')

# 4. Docker images breakdown
run(ssh, 'docker images --format "{{.Repository}}:{{.Tag}} - {{.Size}}" | sort -t"-" -k2 -hr')

# 5. Docker volumes
run(ssh, 'docker volume ls')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/volumes/* 2>/dev/null | sort -hr | head -10')

# 6. Docker overlay2 (where layers are stored)
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/overlay2 2>/dev/null')

# 7. Docker buildx cache
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/buildx 2>/dev/null')

# 8. Logs
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/log 2>/dev/null')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/log/* 2>/dev/null | sort -hr | head -10')

# 9. Container logs specifically
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/containers/*/\*.log 2>/dev/null | sort -hr | head -10')

# 10. Postgres data if local
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/postgresql 2>/dev/null')

# 11. /opt directory (where website is)
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /opt/* 2>/dev/null | sort -hr')

# 12. Home directory
run(ssh, f'du -sh /home/mycosoft/* 2>/dev/null | sort -hr')

# 13. Temp files
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /tmp 2>/dev/null')

# 14. Apt cache
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/cache/apt 2>/dev/null')

# 15. Journal logs
run(ssh, f'echo "{VM_PASS}" | sudo -S journalctl --disk-usage 2>/dev/null')

# 16. Package manager cache
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/cache 2>/dev/null')

# 17. Snap if installed
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /snap 2>/dev/null')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/snapd 2>/dev/null')

# 18. All directories over 1GB
run(ssh, f'echo "{VM_PASS}" | sudo -S find / -type d -exec du -sh {{}} + 2>/dev/null | grep -E "^[0-9.]+G" | sort -hr | head -30')

ssh.close()
print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
