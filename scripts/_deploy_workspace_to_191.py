"""Deploy MYCA workspace stack to VM 191 (already running Ubuntu via cloud-init)."""
import os, sys, time
import paramiko

VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()

print(f"Deploying workspace to VM 191 ({VM_IP})...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
ssh.connect(VM_IP, username=VM_USER, pkey=pkey, timeout=20)

def run(cmd, timeout=180):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

def sudo(cmd, timeout=180):
    full = f"echo {VM_PASSWORD} | sudo -S {cmd}"
    return run(full, timeout=timeout)

# [1] Install Docker
print("[1/7] Installing Docker...")
out, _ = run("which docker 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("apt-get update -qq", timeout=120)
    sudo("apt-get install -y curl ca-certificates", timeout=120)
    out, err = run("curl -fsSL https://get.docker.com | sudo sh", timeout=300)
    print("  Docker install:", out[-100:])
    sudo(f"usermod -aG docker {VM_USER}")
    print("  Docker installed.")
else:
    print("  Docker already present.")

# [2] Docker Compose
print("[2/7] Installing docker-compose-plugin...")
sudo("apt-get install -y docker-compose-plugin python3-pip git -qq", timeout=120)

# [3] Create directory structure
print("[3/7] Creating /opt/myca dirs...")
sudo("mkdir -p /opt/myca/workspace-api /opt/myca/credentials/google /opt/myca/data /opt/myca/logs /opt/myca/n8n")
sudo(f"chown -R {VM_USER}:{VM_USER} /opt/myca")

# [4] Upload workspace files
print("[4/7] Uploading workspace files...")
sftp = ssh.open_sftp()
repo_root = os.path.join(os.path.dirname(__file__), "..")

uploads = [
    ("infra/myca-workspace/docker-compose.yml", "/opt/myca/docker-compose.yml"),
    ("mycosoft_mas/agents/workspace/workspace_api.py", "/opt/myca/workspace-api/workspace_api.py"),
    ("infra/myca-workspace/init-workspace-db.sql", "/opt/myca/workspace-api/init-workspace-db.sql"),
    ("mycosoft_mas/integrations/google_workspace_client.py", "/opt/myca/workspace-api/google_workspace_client.py"),
    ("mycosoft_mas/integrations/discord_client.py", "/opt/myca/workspace-api/discord_client.py"),
    ("mycosoft_mas/integrations/asana_client.py", "/opt/myca/workspace-api/asana_client.py"),
]
for src_rel, dst in uploads:
    src = os.path.join(repo_root, src_rel)
    if os.path.exists(src):
        sftp.put(src, dst)
        print(f"  {os.path.basename(src)}")

# Write __init__.py for imports
with sftp.open("/opt/myca/workspace-api/__init__.py", "w") as f:
    f.write("")

# Write .env
env_content = f"""MYCA_EMAIL=schedule@mycosoft.org
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
BRIDGE_URL=http://192.168.0.190:8999
POSTGRES_PASSWORD=myca_workspace_2026
DB_POSTGRESDB_PASSWORD=myca_workspace_2026
N8N_BASIC_AUTH_USER=myca
N8N_PASSWORD=myca_n8n_2026
GOOGLE_SERVICE_ACCOUNT_KEY=/opt/myca/credentials/google/service_account.json
MYCA_DISCORD_TOKEN=
DISCORD_GUILD_ID=
DISCORD_OPS_CHANNEL_ID=
ASANA_API_KEY=
ASANA_WORKSPACE_ID=
GIT_AUTHOR_NAME=MYCA
GIT_AUTHOR_EMAIL=myca@mycosoft.org
"""
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_content)
print("  .env written")
sftp.close()

# [5] Enable password SSH (for other tools)
print("[5/7] Enabling password auth for SSH...")
sudo("sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config")
sudo("sed -i 's/^#PasswordAuthentication/PasswordAuthentication/' /etc/ssh/sshd_config")
sudo("systemctl restart sshd")

# [6] Start Docker stack
print("[6/7] Starting Docker stack (this pulls images on first run)...")
# Need newgrp to pick up docker group, use sudo docker instead
out, err = sudo("docker compose -f /opt/myca/docker-compose.yml up -d", timeout=300)
print("  stdout:", out[-300:])
if err:
    print("  stderr:", err[-200:])

time.sleep(20)

# [7] Verify
print("[7/7] Verification...")
out, _ = sudo("docker ps --format '{{.Names}}  {{.Status}}'")
print("  Containers:")
for line in out.split("\n"):
    if line.strip():
        print(f"    {line.strip()}")

out, _ = run("curl -s http://localhost:8100/health 2>/dev/null || echo 'API starting...'")
print(f"  Workspace API: {out[:200]}")

out, _ = run("curl -s http://localhost:5679 2>/dev/null | head -1 || echo 'n8n starting...'")
print(f"  n8n: {out[:80]}")

# Git identity
run('git config --global user.name "MYCA"')
run('git config --global user.email "myca@mycosoft.org"')

ssh.close()

print(f"""
VM 191 MYCA WORKSPACE DEPLOYED
  Workspace API:  http://192.168.0.191:8100
  n8n Workflows:  http://192.168.0.191:5679  (user: myca)
  PostgreSQL:     192.168.0.191:5433
  SSH:            ssh mycosoft@192.168.0.191 (key or password)
""")
