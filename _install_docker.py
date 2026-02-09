import paramiko
import time

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print(f"Connecting to MINDEX VM at {mindex_host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Install Docker and dependencies
print("\n=== Installing Docker and dependencies ===")
setup_cmd = """
# Wait for cloud-init to complete if running
cloud-init status --wait 2>/dev/null

# Update and install dependencies
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io docker-compose curl wget git htop net-tools

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker mycosoft

# Check Docker
sudo docker version --format '{{.Server.Version}}'

# Create directories
sudo mkdir -p /opt/mycosoft/ledger
sudo mkdir -p /opt/mycosoft/mindex
sudo chown -R mycosoft:mycosoft /opt/mycosoft

echo "Docker installed successfully!"
"""

stdin, stdout, stderr = ssh.exec_command(setup_cmd, get_pty=True)
# Stream output
while True:
    line = stdout.readline()
    if not line:
        break
    print(line.strip())

print("\nDocker setup complete!")
ssh.close()
