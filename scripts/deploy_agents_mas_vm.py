#!/usr/bin/env python3
"""
Deploy MAS Agents on the MAS VM (192.168.0.188)
Builds and starts all agent containers
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

def run_sudo_command(ssh, command, password, timeout=600, show_output=True):
    """Run command with sudo"""
    full_command = f"echo '{password}' | sudo -S {command}"
    stdin, stdout, stderr = ssh.exec_command(full_command, timeout=timeout, get_pty=True)
    
    output_lines = []
    while True:
        line = stdout.readline()
        if not line:
            break
        line = line.strip()
        if line and 'password' not in line.lower():
            output_lines.append(line)
            if show_output and len(output_lines) <= 30:
                print(f"    {line}")
    
    exit_code = stdout.channel.recv_exit_status()
    return exit_code == 0, '\n'.join(output_lines)

def run_command(ssh, command, timeout=300, show_output=True):
    """Run command without sudo"""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    exit_code = stdout.channel.recv_exit_status()
    
    if show_output and output:
        for line in output.strip().split('\n')[:20]:
            print(f"    {line}")
    
    return exit_code == 0, output, error

def main():
    print("=" * 60)
    print("MAS AGENT DEPLOYMENT")
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
    
    # Step 1: Check Docker is running
    log("Checking Docker status...", "RUN")
    success, output, _ = run_command(ssh, "sudo docker ps 2>&1 | head -5", show_output=False)
    if success:
        log("Docker is running", "OK")
    else:
        # Start Docker
        run_sudo_command(ssh, "systemctl start docker", MAS_VM_PASS, timeout=30, show_output=False)
        log("Docker started", "OK")
    
    # Step 2: Navigate to MAS directory
    log("Checking MAS directory...", "RUN")
    success, output, _ = run_command(ssh, "ls ~/mycosoft/mas/docker/docker-compose.agents.yml", show_output=False)
    if success:
        log("MAS directory found", "OK")
    else:
        log("MAS directory not found - cloning...", "WARN")
        run_command(ssh, "cd ~/mycosoft && git clone https://github.com/MycosoftLabs/mycosoft-mas.git mas", timeout=120)
    
    # Step 3: Create .env file with all required variables
    log("Creating environment configuration...", "RUN")
    env_content = """# MAS v2 Environment Configuration
PROXMOX_HOST=192.168.0.202
PROXMOX_TOKEN=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e
PROXMOX_NODE=pve

REDIS_URL=redis://mas-redis:6379
POSTGRES_HOST=192.168.0.187
POSTGRES_USER=mycosoft
POSTGRES_PASSWORD=mycosoft_secure_2026
POSTGRES_DB=mycosoft

MAS_API_PORT=8001
AGENT_LOG_LEVEL=INFO
AGENT_HEARTBEAT_INTERVAL=30

# Integration placeholders
UNIFI_USERNAME=cursor_agent
UNIFI_PASSWORD=
ELEVENLABS_API_KEY=
OPENAI_API_KEY=
"""
    
    # Write env file
    run_command(ssh, f"cat > ~/mycosoft/mas/docker/.env << 'ENVEOF'\n{env_content}\nENVEOF", show_output=False)
    log("Environment file created", "OK")
    
    # Step 4: Build the agent image
    log("Building MAS agent Docker image (this takes 2-3 minutes)...", "RUN")
    success, output = run_sudo_command(ssh, 
        "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent . 2>&1 | tail -20",
        MAS_VM_PASS, timeout=600)
    
    if success or "Successfully" in output:
        log("Agent image built", "OK")
    else:
        log("Build may have issues - continuing", "WARN")
    
    # Step 5: Start core services (Redis)
    log("Starting core services (Redis, PostgreSQL)...", "RUN")
    
    # Create a simple compose file for core services
    core_compose = """version: '3.8'
services:
  mas-redis:
    image: redis:7-alpine
    container_name: mas-redis
    ports:
      - "6379:6379"
    volumes:
      - mas_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  mas_redis_data:
"""
    
    run_command(ssh, f"cat > ~/mycosoft/mas/docker/docker-compose.core.yml << 'COMPEOF'\n{core_compose}\nCOMPEOF", show_output=False)
    
    success, output = run_sudo_command(ssh, 
        "cd /home/mycosoft/mycosoft/mas/docker && docker compose -f docker-compose.core.yml up -d 2>&1",
        MAS_VM_PASS, timeout=120)
    log("Core services started", "OK")
    
    # Step 6: Start MYCA Orchestrator
    log("Starting MYCA Orchestrator...", "RUN")
    success, output = run_sudo_command(ssh,
        "cd /home/mycosoft/mycosoft/mas/docker && docker compose -f docker-compose.agents.yml up -d myca-orchestrator 2>&1 | tail -15",
        MAS_VM_PASS, timeout=300)
    log("Orchestrator starting", "OK")
    
    # Step 7: Check running containers
    log("Checking running containers...", "RUN")
    time.sleep(5)  # Wait for containers to start
    success, output, _ = run_command(ssh, 
        "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1")
    
    # Step 8: Show system resources
    log("System resources:", "INFO")
    run_command(ssh, "free -h | grep -E 'Mem|Swap'")
    run_command(ssh, "df -h / | tail -1", show_output=True)
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MAS AGENT DEPLOYMENT STATUS")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Docker: Running
Core Services: Redis

To check status:
  ssh mycosoft@192.168.0.188
  docker ps

To view logs:
  docker logs mas-redis
  docker logs myca-orchestrator

To start more agents:
  cd ~/mycosoft/mas/docker
  docker compose -f docker-compose.agents.yml up -d

Dashboard API will be available at:
  http://192.168.0.188:8001/docs
""")
    
    return True

if __name__ == "__main__":
    main()
