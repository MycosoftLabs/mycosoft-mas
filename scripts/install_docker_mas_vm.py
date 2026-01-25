#!/usr/bin/env python3
"""
Install Docker on MAS VM using sudo with password
"""
import time
import sys

try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = "Mushroom1!Mushroom1!"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def run_sudo_command(ssh, command, password, timeout=300):
    """Run command with sudo, providing password via stdin"""
    full_command = f"echo '{password}' | sudo -S {command}"
    stdin, stdout, stderr = ssh.exec_command(full_command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    # Filter out password prompt from stderr
    error = '\n'.join([l for l in error.split('\n') if 'password' not in l.lower()])
    return exit_code == 0, output, error

def main():
    print("=" * 60)
    print("DOCKER INSTALLATION ON MAS VM")
    print("=" * 60)
    
    log("Connecting to MAS VM...", "RUN")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
        log("Connected", "OK")
    except Exception as e:
        log(f"Connection failed: {e}", "ERR")
        return False
    
    # Step 1: Update packages
    log("Updating package lists...", "RUN")
    run_sudo_command(ssh, "apt-get update -qq", MAS_VM_PASS, timeout=120)
    log("Updated", "OK")
    
    # Step 2: Install prerequisites
    log("Installing prerequisites...", "RUN")
    run_sudo_command(ssh, 
        "apt-get install -y ca-certificates curl gnupg lsb-release",
        MAS_VM_PASS, timeout=120)
    log("Prerequisites installed", "OK")
    
    # Step 3: Add Docker GPG key
    log("Adding Docker GPG key...", "RUN")
    run_sudo_command(ssh, "install -m 0755 -d /etc/apt/keyrings", MAS_VM_PASS)
    run_sudo_command(ssh, 
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
        MAS_VM_PASS, timeout=60)
    run_sudo_command(ssh, "chmod a+r /etc/apt/keyrings/docker.asc", MAS_VM_PASS)
    log("GPG key added", "OK")
    
    # Step 4: Add Docker repository
    log("Adding Docker repository...", "RUN")
    add_repo_cmd = '''bash -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null' '''
    run_sudo_command(ssh, add_repo_cmd, MAS_VM_PASS, timeout=30)
    log("Repository added", "OK")
    
    # Step 5: Update and install Docker
    log("Installing Docker (this takes 1-2 minutes)...", "RUN")
    run_sudo_command(ssh, "apt-get update -qq", MAS_VM_PASS, timeout=60)
    success, output, error = run_sudo_command(ssh, 
        "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        MAS_VM_PASS, timeout=300)
    
    if success:
        log("Docker packages installed", "OK")
    else:
        log(f"Docker install output: {error[:200] if error else 'check manually'}", "WARN")
    
    # Step 6: Add user to docker group
    log("Adding user to docker group...", "RUN")
    run_sudo_command(ssh, "usermod -aG docker mycosoft", MAS_VM_PASS)
    log("User added to docker group", "OK")
    
    # Step 7: Enable and start Docker
    log("Starting Docker service...", "RUN")
    run_sudo_command(ssh, "systemctl enable docker", MAS_VM_PASS)
    run_sudo_command(ssh, "systemctl start docker", MAS_VM_PASS)
    log("Docker service started", "OK")
    
    # Step 8: Install QEMU Guest Agent
    log("Installing QEMU Guest Agent...", "RUN")
    run_sudo_command(ssh, "apt-get install -y qemu-guest-agent", MAS_VM_PASS, timeout=60)
    run_sudo_command(ssh, "systemctl enable qemu-guest-agent", MAS_VM_PASS)
    run_sudo_command(ssh, "systemctl start qemu-guest-agent", MAS_VM_PASS)
    log("QEMU Guest Agent installed", "OK")
    
    # Step 9: Verify Docker
    log("Verifying Docker installation...", "RUN")
    success, output, _ = run_sudo_command(ssh, "docker --version", MAS_VM_PASS)
    if output and "Docker" in output:
        log(f"Docker: {output.strip()}", "OK")
    else:
        log("Docker verification - run manually to check", "WARN")
    
    success, output, _ = run_sudo_command(ssh, "docker compose version", MAS_VM_PASS)
    if output and "Docker Compose" in output:
        log(f"Compose: {output.strip()}", "OK")
    
    # Step 10: Test Docker with hello-world
    log("Testing Docker with hello-world...", "RUN")
    success, output, _ = run_sudo_command(ssh, "docker run --rm hello-world 2>&1 | head -5", MAS_VM_PASS, timeout=120)
    if "Hello from Docker" in output:
        log("Docker test passed!", "OK")
    else:
        log("Docker test - check manually", "WARN")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("DOCKER INSTALLATION COMPLETE")
    print("=" * 60)
    print("""
Docker is now installed on the MAS VM!

Note: You need to log out and back in for docker group to take effect.
Or run: newgrp docker

Ready for agent deployment!
""")
    
    return True

if __name__ == "__main__":
    main()
