#!/usr/bin/env python3
"""
Automated MAS VM Setup via SSH
Installs Docker, clones repos, and sets up the MAS stack
"""
import time
import sys

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

# MAS VM Configuration
MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = "REDACTED_VM_SSH_PASSWORD"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def run_ssh_command(ssh, command, timeout=300, show_output=True):
    """Execute command via SSH and return output"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if show_output and output:
            for line in output.strip().split('\n')[:20]:
                print(f"    {line}")
        if show_output and error and exit_code != 0:
            for line in error.strip().split('\n')[:10]:
                print(f"    [stderr] {line}")
        
        return exit_code == 0, output, error
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 60)
    print("MAS VM AUTOMATED SETUP")
    print("=" * 60)
    print(f"Target: {MAS_VM_USER}@{MAS_VM_IP}")
    print()
    
    # Connect via SSH
    log("Connecting to MAS VM via SSH...", "RUN")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
        log("SSH connection established", "OK")
    except Exception as e:
        log(f"SSH connection failed: {e}", "ERR")
        return False
    
    # Step 1: Update system
    log("Updating system packages...", "RUN")
    run_ssh_command(ssh, "sudo apt-get update -qq", timeout=120, show_output=False)
    log("System updated", "OK")
    
    # Step 2: Install prerequisites
    log("Installing prerequisites...", "RUN")
    run_ssh_command(ssh, 
        "sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release git",
        timeout=120, show_output=False)
    log("Prerequisites installed", "OK")
    
    # Step 3: Install Docker
    log("Installing Docker...", "RUN")
    
    # Add Docker's official GPG key
    run_ssh_command(ssh, """
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
sudo chmod a+r /etc/apt/keyrings/docker.gpg
""", timeout=60, show_output=False)
    
    # Add Docker repository
    run_ssh_command(ssh, """
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
""", timeout=30, show_output=False)
    
    # Install Docker
    run_ssh_command(ssh, "sudo apt-get update -qq", timeout=60, show_output=False)
    success, _, _ = run_ssh_command(ssh, 
        "sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        timeout=180, show_output=False)
    
    if success:
        log("Docker installed", "OK")
    else:
        log("Docker installation may have issues", "WARN")
    
    # Add user to docker group
    run_ssh_command(ssh, "sudo usermod -aG docker mycosoft", timeout=30, show_output=False)
    log("User added to docker group", "OK")
    
    # Step 4: Start Docker
    log("Starting Docker service...", "RUN")
    run_ssh_command(ssh, "sudo systemctl enable docker && sudo systemctl start docker", timeout=30, show_output=False)
    
    # Verify Docker
    success, output, _ = run_ssh_command(ssh, "sudo docker --version", timeout=30)
    if success and "Docker" in output:
        log(f"Docker verified: {output.strip()}", "OK")
    else:
        log("Docker verification failed", "WARN")
    
    # Step 5: Install QEMU Guest Agent (for Proxmox)
    log("Installing QEMU Guest Agent...", "RUN")
    run_ssh_command(ssh, "sudo apt-get install -y -qq qemu-guest-agent", timeout=60, show_output=False)
    run_ssh_command(ssh, "sudo systemctl enable qemu-guest-agent && sudo systemctl start qemu-guest-agent", timeout=30, show_output=False)
    log("QEMU Guest Agent installed", "OK")
    
    # Step 6: Create directory structure
    log("Creating directory structure...", "RUN")
    run_ssh_command(ssh, "mkdir -p ~/mycosoft", timeout=10, show_output=False)
    log("Directories created", "OK")
    
    # Step 7: Clone MAS repository
    log("Cloning MAS repository...", "RUN")
    success, output, error = run_ssh_command(ssh, 
        "cd ~/mycosoft && git clone https://github.com/MycosoftLabs/mycosoft-mas.git mas 2>&1 || (cd mas && git pull origin main)",
        timeout=120)
    if success:
        log("MAS repository cloned", "OK")
    else:
        log(f"Clone result: {output[:100] if output else error[:100]}", "WARN")
    
    # Step 8: Check MAS files
    log("Verifying MAS files...", "RUN")
    success, output, _ = run_ssh_command(ssh, "ls -la ~/mycosoft/mas/docker/ 2>&1 | head -10")
    if success and "docker-compose" in output:
        log("MAS files verified", "OK")
    else:
        log("MAS files check", "WARN")
    
    # Step 9: Create .env file for agents
    log("Creating environment configuration...", "RUN")
    env_content = """# MAS v2 Environment Configuration
# Generated by setup script

# Proxmox API
PROXMOX_HOST=192.168.0.202
PROXMOX_TOKEN=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e

# Redis
REDIS_URL=redis://localhost:6379

# PostgreSQL (from sandbox)
DATABASE_URL=postgresql://mycosoft:mycosoft_secure_2026@192.168.0.187:5432/mycosoft

# MAS Configuration
MAS_VM_IP=192.168.0.188
SANDBOX_VM_IP=192.168.0.187

# Agent Settings
AGENT_LOG_LEVEL=INFO
AGENT_HEARTBEAT_INTERVAL=30
"""
    
    run_ssh_command(ssh, f'echo "{env_content}" > ~/mycosoft/mas/.env', timeout=10, show_output=False)
    log("Environment file created", "OK")
    
    # Step 10: Pull Docker images (in background)
    log("Pulling base Docker images (this runs in background)...", "RUN")
    run_ssh_command(ssh, 
        "cd ~/mycosoft/mas && sudo docker pull python:3.11-slim &",
        timeout=10, show_output=False)
    log("Docker pull started in background", "OK")
    
    # Step 11: System info
    log("Gathering system info...", "RUN")
    success, output, _ = run_ssh_command(ssh, "free -h | grep Mem")
    if output:
        log(f"Memory: {output.strip()}", "INFO")
    
    success, output, _ = run_ssh_command(ssh, "nproc")
    if output:
        log(f"CPU cores: {output.strip()}", "INFO")
    
    success, output, _ = run_ssh_command(ssh, "df -h / | tail -1")
    if output:
        log(f"Disk: {output.strip()}", "INFO")
    
    # Close SSH
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MAS VM SETUP COMPLETE")
    print("=" * 60)
    print(f"""
VM Details:
  IP: 192.168.0.188
  User: mycosoft
  Docker: Installed
  MAS Repo: ~/mycosoft/mas

Next Steps:
  1. SSH in: ssh mycosoft@192.168.0.188
  2. Build agents: cd ~/mycosoft/mas && docker compose -f docker/docker-compose.agents.yml build
  3. Start agents: docker compose -f docker/docker-compose.agents.yml up -d

The VM is ready for MAS agent deployment!
""")
    
    return True

if __name__ == "__main__":
    main()
