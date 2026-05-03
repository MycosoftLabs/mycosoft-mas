"""Try NAS mount credential combinations using only environment-provided passwords.

Do not add literal passwords to this file (policy: no-hardcoded-secrets).
"""
from __future__ import annotations

import os
import sys
import time

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mindex_host = os.environ.get("MINDEX_SSH_HOST", "192.168.0.189")
user = os.environ.get("MINDEX_SSH_USER", "mycosoft")
passwd = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
extra_candidates = [
    p.strip()
    for p in os.environ.get("NAS_MOUNT_PASSWORD_CANDIDATES", "").split(",")
    if p.strip()
]

if not passwd and not extra_candidates:
    print("Set VM_PASSWORD (SSH) and optionally NAS_MOUNT_PASSWORD_CANDIDATES=comma,separated")
    sys.exit(1)

print("Connecting over SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd or extra_candidates[0], timeout=30)

attempts: list[tuple[str, str]] = []
if passwd:
    attempts.append((user, passwd))
for cand in extra_candidates:
    attempts.append((user, cand))

for username, password in attempts:
    print(f"\nTrying: username={username}")
    cmd = f'''
sudo bash -c 'cat > /etc/samba/mycosoft-nas.creds << "CREDEOF"
username={username}
password={password}
CREDEOF'
sudo chmod 600 /etc/samba/mycosoft-nas.creds
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas -o credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,uid=1000,gid=1000 2>&1
if mountpoint -q /mnt/mycosoft-nas; then
    echo "SUCCESS with {username}!"
    ls /mnt/mycosoft-nas/ | head -5
    exit 0
fi
'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(8)
    result = stdout.read().decode("utf-8", errors="replace")
    print(result)
    if "SUCCESS" in result:
        break

ssh.close()
