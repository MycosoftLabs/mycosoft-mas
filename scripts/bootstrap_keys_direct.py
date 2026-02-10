#!/usr/bin/env python3
"""
Directly bootstrap API keys via SQL.
"""

import paramiko
import secrets
import hashlib

VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
VM_189 = "192.168.0.189"

def ssh_exec(host, cmd, timeout=60):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=VM_USER, password=VM_PASS, timeout=30)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    code = stdout.channel.recv_exit_status()
    ssh.close()
    return out, err, code

# Generate keys
admin_key = f"myco_admin_{secrets.token_urlsafe(32)}"
mas_key = f"myco_mas_{secrets.token_urlsafe(32)}"

admin_hash = hashlib.sha256(admin_key.encode()).hexdigest()
mas_hash = hashlib.sha256(mas_key.encode()).hexdigest()

print("=== Checking existing keys ===")
out, err, code = ssh_exec(VM_189, 
    "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT name, service FROM api_keys\""
)
print(out)

if "bootstrap-admin" in out or "mas-service" in out:
    print("Keys already exist!")
else:
    print("\n=== Creating Admin Key ===")
    # Use single quotes inside the JSON and escape for shell
    admin_scopes = '[\\\"admin\\\", \\\"keys:manage\\\", \\\"keys:create\\\", \\\"keys:revoke\\\", \\\"read\\\", \\\"write\\\"]'
    sql = f"INSERT INTO api_keys (key_hash, key_prefix, name, service, scopes, rate_limit_per_minute, rate_limit_per_day) VALUES ('{admin_hash}', '{admin_key[:12]}', 'bootstrap-admin', 'admin', '{admin_scopes}'::jsonb, 600, 50000);"
    
    out, err, code = ssh_exec(VM_189, 
        f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql}"'
    )
    print(out)
    if code == 0 and "INSERT" in out:
        print(f"MYCORRHIZAE_ADMIN_API_KEY={admin_key}")
    elif "already exists" in err.lower() or "duplicate" in err.lower():
        print("Admin key already exists")
    else:
        print(f"Error: {err}")

    print("\n=== Creating MAS Service Key ===")
    mas_scopes = '[\\\"read\\\", \\\"write\\\"]'
    sql = f"INSERT INTO api_keys (key_hash, key_prefix, name, service, scopes, rate_limit_per_minute, rate_limit_per_day) VALUES ('{mas_hash}', '{mas_key[:12]}', 'mas-service', 'mas', '{mas_scopes}'::jsonb, 600, 50000);"
    
    out, err, code = ssh_exec(VM_189, 
        f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql}"'
    )
    print(out)
    if code == 0 and "INSERT" in out:
        print(f"MYCORRHIZAE_API_KEY={mas_key}")
    elif "already exists" in err.lower() or "duplicate" in err.lower():
        print("MAS key already exists")
    else:
        print(f"Error: {err}")

print("\n=== Verifying Keys ===")
out, err, code = ssh_exec(VM_189, 
    "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT name, service, key_prefix FROM api_keys\""
)
print(out)

print("\n=== Keys Generated ===")
print(f"MYCORRHIZAE_ADMIN_API_KEY={admin_key}")
print(f"MYCORRHIZAE_API_KEY={mas_key}")
print("\nAdd MYCORRHIZAE_API_KEY to MAS environment to enable MAS -> Mycorrhizae calls.")
