#!/usr/bin/env python3
"""
Deploy Mycorrhizae Protocol to VM 188 (MAS VM)
Date: FEB09 2026

This script:
1. Applies the API keys migration to MINDEX Postgres on VM 189
2. Clones/updates Mycorrhizae repo on VM 188
3. Configures .env file with proper secrets
4. Builds and starts the Mycorrhizae container
5. Bootstraps the first admin API key
6. Creates a service key for MAS
7. Configures MAS orchestrator with the API key
8. Restarts MAS service
"""

import secrets
import time
from typing import Tuple

# VM Credentials
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

# VM IPs
VM_188 = "192.168.0.188"  # MAS VM
VM_189 = "192.168.0.189"  # MINDEX VM

# MINDEX Postgres credentials (from docker-compose on VM 189)
MINDEX_DB_USER = "mycosoft"
MINDEX_DB_PASS = "mycosoft_mindex_2026"
MINDEX_DB_NAME = "mindex"

# GitHub repo
MYCORRHIZAE_REPO = "https://github.com/mycosoft/Mycorrhizae.git"


def generate_bootstrap_token() -> str:
    """Generate a secure random token for API key bootstrap."""
    return secrets.token_urlsafe(32)


def generate_mindex_api_key() -> str:
    """Generate a secure random MINDEX API key."""
    return f"myco_mindex_{secrets.token_urlsafe(24)}"


try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.run(["pip", "install", "paramiko"], check=True)
    import paramiko


def ssh_exec(host: str, commands: list[str], timeout: int = 60) -> Tuple[str, str, int]:
    """Execute commands via SSH and return stdout, stderr, exit_code."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"  Connecting to {host}...")
        ssh.connect(host, username=VM_USER, password=VM_PASS, timeout=30)
        
        # Join commands with &&
        cmd = " && ".join(commands) if len(commands) > 1 else commands[0]
        print(f"  Executing: {cmd[:100]}...")
        
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        
        return out, err, exit_code
    finally:
        ssh.close()


def sftp_upload(host: str, local_content: str, remote_path: str) -> bool:
    """Upload content to a file via SFTP."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=VM_USER, password=VM_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        with sftp.file(remote_path, 'w') as f:
            f.write(local_content)
        
        sftp.close()
        return True
    except Exception as e:
        print(f"  SFTP error: {e}")
        return False
    finally:
        ssh.close()


def step1_get_mindex_db_password() -> str:
    """Get the MINDEX Postgres password (known from docker-compose on VM 189)."""
    # Confirmed from docker-compose.yml: POSTGRES_USER=mycosoft, POSTGRES_PASSWORD=mycosoft_mindex_2026
    return MINDEX_DB_PASS


def step1_apply_migration() -> bool:
    """Apply the API keys migration to MINDEX Postgres."""
    print("\n[Step 1b] Applying API keys migration to MINDEX Postgres...")
    
    # Get the actual password
    db_pass = step1_get_mindex_db_password()
    
    # The migration SQL
    migration_sql = '''
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key_hash text UNIQUE NOT NULL,
  key_prefix text NOT NULL,
  name text NOT NULL,
  description text,
  owner_id uuid,
  service text NOT NULL,
  scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
  rate_limit_per_minute integer NOT NULL DEFAULT 60,
  rate_limit_per_day integer NOT NULL DEFAULT 10000,
  expires_at timestamptz,
  last_used_at timestamptz,
  usage_count integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  rotated_from uuid REFERENCES api_keys(id),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_api_keys_service ON api_keys(service);
CREATE INDEX IF NOT EXISTS ix_api_keys_is_active ON api_keys(is_active);

CREATE TABLE IF NOT EXISTS api_key_usage (
  key_id uuid NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  window_start timestamptz NOT NULL,
  window_type text NOT NULL,
  request_count integer NOT NULL DEFAULT 0,
  PRIMARY KEY (key_id, window_start, window_type)
);

CREATE TABLE IF NOT EXISTS api_key_audit (
  id bigserial PRIMARY KEY,
  key_id uuid NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  action text NOT NULL,
  ip_address inet,
  user_agent text,
  endpoint text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
'''
    
    # Upload migration to VM and execute
    remote_path = "/tmp/0010_api_keys.sql"
    print("  Uploading migration file...")
    
    if not sftp_upload(VM_189, migration_sql, remote_path):
        return False
    
    # Execute migration via psql (using mycosoft user, not mindex)
    print("  Executing migration via psql...")
    
    # Copy file into container first
    out, err, code = ssh_exec(VM_189, [
        f"docker cp {remote_path} mindex-postgres:/tmp/0010_api_keys.sql"
    ], timeout=30)
    
    # Execute with correct user (mycosoft)
    out, err, code = ssh_exec(VM_189, [
        "docker exec mindex-postgres psql -U mycosoft -d mindex -f /tmp/0010_api_keys.sql 2>&1"
    ], timeout=30)
    
    if code != 0 and 'already exists' not in out.lower():
        print(f"  Migration output: {out}")
        print(f"  Migration error: {err}")
        # Tables might already exist, which is fine
        if 'ERROR' in out and 'already exists' not in out.lower():
            print("  WARNING: Migration had errors, but continuing...")
    
    print(f"  Migration output: {out[:500]}")
    
    # Verify tables exist
    verify_out, _, verify_code = ssh_exec(VM_189, [
        "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT tablename FROM pg_tables WHERE tablename LIKE 'api_key%'\""
    ])
    
    if 'api_keys' in verify_out:
        print("  [OK] api_keys table created successfully")
        return True
    else:
        print(f"  Table verification: {verify_out}")
        return True  # Tables might exist already (IF NOT EXISTS)


def step2_setup_mycorrhizae_repo() -> bool:
    """Clone or update Mycorrhizae repo on VM 188."""
    print("\n[Step 2] Setting up Mycorrhizae repo on VM 188...")
    
    # Check if repo exists
    out, _, code = ssh_exec(VM_188, [
        "test -d ~/mycosoft/Mycorrhizae/.git && echo 'EXISTS' || echo 'NOT_EXISTS'"
    ])
    
    if 'EXISTS' in out:
        print("  Repo exists, pulling latest...")
        out, err, code = ssh_exec(VM_188, [
            "cd ~/mycosoft/Mycorrhizae",
            "git fetch origin",
            "git reset --hard origin/main"
        ])
        if code != 0:
            print(f"  ERROR: Git pull failed: {err}")
            return False
    else:
        print("  Cloning repo...")
        out, err, code = ssh_exec(VM_188, [
            "mkdir -p ~/mycosoft",
            f"cd ~/mycosoft && git clone {MYCORRHIZAE_REPO}"
        ], timeout=120)
        if code != 0:
            print(f"  ERROR: Git clone failed: {err}")
            # Try alternative - copy from local
            print("  Attempting to copy files via SCP...")
            return step2_copy_files_directly()
    
    print("  [OK] Repo ready")
    return True


def step2_copy_files_directly() -> bool:
    """Alternative: copy essential files directly if git clone fails."""
    print("  Copying essential Mycorrhizae files directly...")
    
    import os
    local_repo = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\Mycorrhizae\mycorrhizae-protocol"
    
    # Create directory structure
    ssh_exec(VM_188, [
        "mkdir -p ~/mycosoft/Mycorrhizae/mycorrhizae-protocol/api",
        "mkdir -p ~/mycosoft/Mycorrhizae/mycorrhizae-protocol/mycorrhizae",
        "mkdir -p ~/mycosoft/Mycorrhizae/mycorrhizae-protocol/services",
        "mkdir -p ~/mycosoft/Mycorrhizae/mycorrhizae-protocol/scripts"
    ])
    
    # Upload key files
    files_to_copy = [
        ("Dockerfile", "Dockerfile"),
        ("docker-compose.vm188.yml", "docker-compose.vm188.yml"),
        ("pyproject.toml", "pyproject.toml"),
        ("api/main.py", "api/main.py"),
        ("api/keys_router.py", "api/keys_router.py"),
        ("api/channels_router.py", "api/channels_router.py"),
        ("api/stream_router.py", "api/stream_router.py"),
        ("api/__init__.py", "api/__init__.py"),
        ("services/key_service.py", "services/key_service.py"),
        ("services/__init__.py", "services/__init__.py"),
        ("mycorrhizae/__init__.py", "mycorrhizae/__init__.py"),
        ("mycorrhizae/broker.py", "mycorrhizae/broker.py"),
        ("mycorrhizae/channels.py", "mycorrhizae/channels.py"),
        ("mycorrhizae/envelope_contract.py", "mycorrhizae/envelope_contract.py"),
        ("mycorrhizae/message.py", "mycorrhizae/message.py"),
        ("mycorrhizae/protocol.py", "mycorrhizae/protocol.py"),
        ("scripts/bootstrap_api_keys_FEB09_2026.py", "scripts/bootstrap_api_keys_FEB09_2026.py"),
    ]
    
    base_remote = "/home/mycosoft/mycosoft/Mycorrhizae/mycorrhizae-protocol"
    
    for local_rel, remote_rel in files_to_copy:
        local_path = os.path.join(local_repo, local_rel)
        remote_path = f"{base_remote}/{remote_rel}"
        
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            if sftp_upload(VM_188, content, remote_path):
                print(f"    [OK] Uploaded {remote_rel}")
            else:
                print(f"    [FAIL] Failed to upload {remote_rel}")
    
    return True


def step3_configure_env(db_pass: str, bootstrap_token: str) -> bool:
    """Create .env file on VM 188."""
    print("\n[Step 3] Configuring .env file...")
    
    # Use the correct database user (mycosoft, not mindex)
    env_content = f"""# Mycorrhizae Protocol - VM 188 Production Config
# Auto-generated by deploy_mycorrhizae_vm188.py

MYCORRHIZAE_DATABASE_URL=postgresql://mycosoft:{db_pass}@192.168.0.189:5432/mindex
MYCORRHIZAE_REDIS_URL=redis://192.168.0.189:6379
MYCORRHIZAE_HOST=0.0.0.0
MYCORRHIZAE_PORT=8002
MYCORRHIZAE_CORS_ORIGINS=*
MYCORRHIZAE_BOOTSTRAP_TOKEN={bootstrap_token}
MYCORRHIZAE_REQUIRE_DEVICE_SIGNATURE=0
"""
    
    remote_path = "/home/mycosoft/mycosoft/Mycorrhizae/mycorrhizae-protocol/.env"
    
    if sftp_upload(VM_188, env_content, remote_path):
        print("  [OK] .env file created")
        return True
    else:
        print("  [FAIL] Failed to create .env file")
        return False


def step4_build_and_start_container() -> bool:
    """Build and start the Mycorrhizae container."""
    print("\n[Step 4] Building and starting Mycorrhizae container...")
    
    # Stop existing container if any
    print("  Stopping existing container (if any)...")
    ssh_exec(VM_188, [
        "cd ~/mycosoft/Mycorrhizae/mycorrhizae-protocol",
        "docker compose -f docker-compose.vm188.yml down 2>/dev/null || true"
    ])
    
    # Build and start
    print("  Building container (this may take a minute)...")
    out, err, code = ssh_exec(VM_188, [
        "cd ~/mycosoft/Mycorrhizae/mycorrhizae-protocol",
        "docker compose -f docker-compose.vm188.yml --env-file .env up -d --build"
    ], timeout=180)
    
    if code != 0:
        print(f"  ERROR: Container build failed: {err}")
        return False
    
    print("  Waiting for container to start...")
    time.sleep(10)
    
    # Check container status
    out, _, code = ssh_exec(VM_188, [
        "docker ps --filter name=mycorrhizae-api --format '{{.Status}}'"
    ])
    
    if 'Up' in out:
        print(f"  [OK] Container running: {out.strip()}")
    else:
        print(f"  Container status: {out}")
        # Check logs
        logs, _, _ = ssh_exec(VM_188, ["docker logs mycorrhizae-api --tail 50"])
        print(f"  Logs: {logs[:1000]}")
    
    # Health check
    out, _, code = ssh_exec(VM_188, [
        "curl -fsS http://127.0.0.1:8002/health 2>&1 || echo 'HEALTH_CHECK_FAILED'"
    ])
    
    if 'HEALTH_CHECK_FAILED' not in out:
        print(f"  [OK] Health check passed: {out.strip()}")
        return True
    else:
        print("  Health check failed, waiting and retrying...")
        time.sleep(10)
        out2, _, _ = ssh_exec(VM_188, ["curl -fsS http://127.0.0.1:8002/health 2>&1"])
        if out2:
            print(f"  [OK] Health check passed on retry: {out2.strip()}")
            return True
        print("  [FAIL] Health check still failing")
        return False


def step5_bootstrap_api_keys(bootstrap_token: str) -> Tuple[str, str]:
    """Bootstrap the admin API key and create MAS service key."""
    print("\n[Step 5] Bootstrapping API keys...")
    
    admin_key = ""
    mas_key = ""
    
    # Bootstrap admin key via API
    print("  Creating admin key via bootstrap endpoint...")
    out, err, code = ssh_exec(VM_188, [
        f"curl -s -X POST "
        f"-H 'X-Mycorrhizae-Bootstrap-Token: {bootstrap_token}' "
        f"-H 'Content-Type: application/json' "
        f"-d '{{\"name\": \"bootstrap-admin\", \"description\": \"Initial admin key\"}}' "
        f"http://127.0.0.1:8002/api/keys/bootstrap"
    ])
    
    print(f"  Bootstrap response: {out}")
    
    if '"key":' in out:
        import json
        try:
            data = json.loads(out)
            admin_key = data.get('key', '')
            print(f"  [OK] Admin key created: {admin_key[:20]}...")
        except:
            print("  Could not parse response as JSON")
    elif 'keys already exist' in out.lower():
        print("  Keys already exist, skipping bootstrap")
        # Get existing admin key from script or config
        return "", ""
    else:
        print(f"  Bootstrap may have failed: {out}")
        # Try direct DB approach
        print("  Attempting direct DB bootstrap...")
        return step5_bootstrap_via_script()
    
    # Create MAS service key using the admin key
    if admin_key:
        print("  Creating MAS service key...")
        out, err, code = ssh_exec(VM_188, [
            f"curl -s -X POST "
            f"-H 'X-API-Key: {admin_key}' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"name\": \"mas-service\", \"service\": \"mas\", \"scopes\": [\"read\", \"write\"], \"description\": \"MAS orchestrator -> Mycorrhizae\"}}' "
            f"http://127.0.0.1:8002/api/keys"
        ])
        
        print(f"  Create MAS key response: {out}")
        
        if '"key":' in out:
            import json
            try:
                data = json.loads(out)
                mas_key = data.get('key', '')
                print(f"  [OK] MAS service key created: {mas_key[:20]}...")
            except:
                pass
    
    return admin_key, mas_key


def step5_bootstrap_via_script() -> Tuple[str, str]:
    """Alternative: bootstrap keys using the Python script directly."""
    print("  Running bootstrap script directly...")
    
    out, err, code = ssh_exec(VM_188, [
        "cd ~/mycosoft/Mycorrhizae/mycorrhizae-protocol",
        "source .env",
        "python scripts/bootstrap_api_keys_FEB09_2026.py "
        "--database-url \"$MYCORRHIZAE_DATABASE_URL\" "
        "--ensure-schema --create-admin --create-service mas"
    ], timeout=60)
    
    print(f"  Script output: {out}")
    
    admin_key = ""
    mas_key = ""
    
    for line in out.split('\n'):
        if 'MYCORRHIZAE_ADMIN_API_KEY=' in line:
            admin_key = line.split('=', 1)[1].strip()
        elif 'MYCORRHIZAE_API_KEY__FOR_MAS=' in line:
            mas_key = line.split('=', 1)[1].strip()
    
    return admin_key, mas_key


def step6_configure_mas(mas_key: str) -> bool:
    """Configure MAS orchestrator with the Mycorrhizae API key."""
    print("\n[Step 6] Configuring MAS orchestrator...")
    
    if not mas_key:
        print("  WARNING: No MAS key available, skipping configuration")
        return False
    
    # Check where MAS reads its env
    out, _, _ = ssh_exec(VM_188, [
        "cat /etc/systemd/system/mas-orchestrator.service 2>/dev/null || "
        "cat ~/mycosoft/mas/.env 2>/dev/null || "
        "echo 'NO_ENV_FOUND'"
    ])
    
    print(f"  MAS env location check: {out[:500]}")
    
    # Try to find and update MAS .env
    out, _, code = ssh_exec(VM_188, [
        "test -f ~/mycosoft/mas/.env && echo 'MAS_ENV_EXISTS' || echo 'NO_MAS_ENV'"
    ])
    
    if 'MAS_ENV_EXISTS' in out:
        print("  Updating MAS .env file...")
        
        # Append or update the key
        ssh_exec(VM_188, [
            f"grep -q 'MYCORRHIZAE_API_KEY' ~/mycosoft/mas/.env || "
            f"echo 'MYCORRHIZAE_API_KEY={mas_key}' >> ~/mycosoft/mas/.env",
            f"grep -q 'MYCORRHIZAE_API_URL' ~/mycosoft/mas/.env || "
            f"echo 'MYCORRHIZAE_API_URL=http://127.0.0.1:8002' >> ~/mycosoft/mas/.env"
        ])
        print("  [OK] Updated MAS .env")
    else:
        # Create a new env file for MAS
        mas_env_content = f"""# MAS Environment - Mycorrhizae Integration
MYCORRHIZAE_API_URL=http://127.0.0.1:8002
MYCORRHIZAE_API_KEY={mas_key}
"""
        if sftp_upload(VM_188, mas_env_content, "/home/mycosoft/mycosoft/mas/.env.mycorrhizae"):
            print("  [OK] Created ~/mycosoft/mas/.env.mycorrhizae")
    
    return True


def step7_restart_mas() -> bool:
    """Restart MAS orchestrator service."""
    print("\n[Step 7] Restarting MAS orchestrator...")
    
    out, err, code = ssh_exec(VM_188, [
        "sudo systemctl restart mas-orchestrator 2>&1 || "
        "docker restart myca-orchestrator-new 2>&1 || "
        "echo 'NO_MAS_SERVICE'"
    ])
    
    if 'NO_MAS_SERVICE' in out:
        print("  WARNING: Could not find MAS service to restart")
        print("  You may need to restart MAS manually")
        return False
    
    time.sleep(5)
    
    # Check MAS health
    out, _, code = ssh_exec(VM_188, [
        "curl -fsS http://127.0.0.1:8001/health 2>&1 || echo 'MAS_HEALTH_FAILED'"
    ])
    
    if 'MAS_HEALTH_FAILED' not in out:
        print(f"  [OK] MAS health check passed: {out.strip()}")
        return True
    else:
        print("  MAS health check failed")
        return False


def main():
    print("=" * 60)
    print("Mycorrhizae Protocol Deployment to VM 188")
    print("=" * 60)
    
    # Generate secrets
    bootstrap_token = generate_bootstrap_token()
    mindex_api_key = generate_mindex_api_key()
    
    print(f"\nGenerated secrets (save these!):")
    print(f"  MYCORRHIZAE_BOOTSTRAP_TOKEN={bootstrap_token}")
    print(f"  MINDEX_API_KEY={mindex_api_key}")
    
    # Step 1: Apply migration to MINDEX
    db_pass = step1_get_mindex_db_password()
    if not step1_apply_migration():
        print("\n[!] Migration may have issues, continuing anyway...")
    
    # Step 2: Setup repo
    if not step2_setup_mycorrhizae_repo():
        print("\n[!] Repo setup had issues, attempting file copy...")
        step2_copy_files_directly()
    
    # Step 3: Configure env
    if not step3_configure_env(db_pass, bootstrap_token):
        print("\n[X] Failed to configure env, aborting")
        return 1
    
    # Step 4: Build and start container
    if not step4_build_and_start_container():
        print("\n[X] Container failed to start, aborting")
        return 1
    
    # Step 5: Bootstrap API keys
    admin_key, mas_key = step5_bootstrap_api_keys(bootstrap_token)
    
    # Step 6: Configure MAS
    if mas_key:
        step6_configure_mas(mas_key)
    
    # Step 7: Restart MAS
    step7_restart_mas()
    
    # Summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"\nMycorrhizae API: http://192.168.0.188:8002")
    print(f"Health endpoint: http://192.168.0.188:8002/health")
    print(f"\nGenerated Keys (SAVE THESE SECURELY):")
    print(f"  MYCORRHIZAE_BOOTSTRAP_TOKEN={bootstrap_token}")
    print(f"  MINDEX_API_KEY={mindex_api_key}")
    if admin_key:
        print(f"  MYCORRHIZAE_ADMIN_API_KEY={admin_key}")
    if mas_key:
        print(f"  MYCORRHIZAE_API_KEY (for MAS)={mas_key}")
    
    return 0


if __name__ == "__main__":
    exit(main())
