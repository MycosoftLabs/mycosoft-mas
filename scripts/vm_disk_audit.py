import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=120):
    print(f'\n$ {cmd}')
    print('-' * 60)
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    return output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=' * 80)
print('VM DISK SPACE AUDIT')
print('=' * 80)

print('\n\n### 1. OVERALL DISK USAGE ###')
run(ssh, 'df -h')

print('\n\n### 2. TOP 20 LARGEST DIRECTORIES (from /) ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -h --max-depth=2 / 2>/dev/null | sort -hr | head -30')

print('\n\n### 3. DOCKER DISK USAGE (DETAILED) ###')
run(ssh, 'docker system df -v')

print('\n\n### 4. DOCKER IMAGES (by size) ###')
run(ssh, 'docker images --format "table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}" | sort -k3 -hr | head -20')

print('\n\n### 5. DOCKER VOLUMES ###')
run(ssh, 'docker volume ls')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/volumes/* 2>/dev/null | sort -hr')

print('\n\n### 6. DOCKER BUILD CACHE ###')
run(ssh, 'docker builder du')

print('\n\n### 7. /var/lib/docker SIZE ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/docker/* 2>/dev/null | sort -hr')

print('\n\n### 8. /opt/mycosoft SIZE ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /opt/mycosoft')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /opt/mycosoft/* 2>/dev/null | sort -hr')

print('\n\n### 9. DATABASE FILES (if stored locally) ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S find / -name "*.db" -o -name "*.sqlite" -o -name "*.mdb" 2>/dev/null | head -20')
run(ssh, f'echo "{VM_PASS}" | sudo -S find / -type d -name "postgres*" -o -name "pgdata" 2>/dev/null | head -10')

print('\n\n### 10. LOG FILES ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/log')
run(ssh, f'echo "{VM_PASS}" | sudo -S ls -lhS /var/log/*.log 2>/dev/null | head -10')

print('\n\n### 11. CONTAINER DATA VOLUMES ###')
run(ssh, 'docker inspect --format "{{.Name}}: {{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Type}}) {{end}}" $(docker ps -aq) 2>/dev/null')

print('\n\n### 12. POSTGRES DATA (if exists) ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/lib/postgresql 2>/dev/null || echo "Not found"')
run(ssh, 'docker exec mindex-postgres du -sh /var/lib/postgresql/data 2>/dev/null || echo "Container not accessible"')

print('\n\n### 13. OLD/DANGLING IMAGES ###')
run(ssh, 'docker images -f "dangling=true" --format "{{.ID}} {{.Size}}"')

print('\n\n### 14. STOPPED CONTAINERS ###')
run(ssh, 'docker ps -a --filter "status=exited" --format "table {{.Names}}\\t{{.Status}}\\t{{.Size}}"')

print('\n\n### 15. JOURNAL/SYSTEMD LOGS ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S journalctl --disk-usage')

print('\n\n### 16. APT CACHE ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/cache/apt')

print('\n\n### 17. CLOUDFLARED LOGS ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -sh /var/log/cloudflared* 2>/dev/null || echo "Not found"')

print('\n\n### 18. SUMMARY - TOP SPACE CONSUMERS ###')
run(ssh, f'echo "{VM_PASS}" | sudo -S du -h --max-depth=1 / 2>/dev/null | sort -hr | head -15')

ssh.close()

print('\n\n' + '=' * 80)
print('AUDIT COMPLETE')
print('=' * 80)
