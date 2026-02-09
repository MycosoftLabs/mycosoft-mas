import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Testing database insert individually...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Run commands separately
cmds = [
    "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"INSERT INTO memory.entries (scope, namespace, key, value) VALUES ('system', 'test', 'key1', '{\\\"hello\\\": \\\"world\\\"}') ON CONFLICT (scope, namespace, key) DO NOTHING;\"",
    "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT COUNT(*) FROM memory.entries;\"",
    "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT * FROM memory.entries LIMIT 3;\"",
]

for cmd in cmds:
    print(f"\n=== Running: {cmd[:60]}... ===")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(5)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"Out: {out}")
    if err:
        print(f"Err: {err}")

ssh.close()
