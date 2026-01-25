#!/usr/bin/env python3
"""
Start MAS Agents on VM - Fixed sudo handling
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
MAS_VM_PASS = "REDACTED_VM_SSH_PASSWORD"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def run_cmd(ssh, command, timeout=300, show_output=True):
    """Run command with password piped to sudo"""
    # Wrap command in bash -c for proper execution
    if "sudo" in command:
        # Use -S flag to read password from stdin
        cmd = f"echo '{MAS_VM_PASS}' | sudo -S bash -c '{command.replace('sudo ', '')}'"
    else:
        cmd = command
    
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    # Filter password prompts
    output_lines = [l for l in output.split('\n') if l.strip() and 'password' not in l.lower()]
    error_lines = [l for l in error.split('\n') if l.strip() and 'password' not in l.lower()]
    
    if show_output and output_lines:
        for line in output_lines[:25]:
            print(f"    {line}")
    
    return exit_code == 0, '\n'.join(output_lines), '\n'.join(error_lines)

def main():
    print("=" * 60)
    print("MAS AGENT STARTUP")
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
    
    # Step 1: Check current containers
    log("Checking current Docker containers...", "RUN")
    success, output, _ = run_cmd(ssh, "sudo docker ps -a --format 'table {{.Names}}\\t{{.Status}}'", show_output=True)
    
    # Step 2: Build the agent image
    log("Building MAS agent image...", "RUN")
    build_cmd = "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent . 2>&1 | tail -25"
    success, output, error = run_cmd(ssh, f"sudo {build_cmd}", timeout=600)
    
    if "Successfully" in output or "exporting to image" in output.lower():
        log("Agent image built successfully", "OK")
    else:
        log(f"Build status: Check output above", "WARN")
    
    # Step 3: Start Redis container
    log("Starting Redis container...", "RUN")
    redis_cmd = "docker run -d --name mas-redis --restart unless-stopped -p 6379:6379 redis:7-alpine 2>&1 || docker start mas-redis 2>&1"
    success, output, _ = run_cmd(ssh, f"sudo {redis_cmd}")
    log("Redis container ready", "OK")
    
    # Step 4: Start the agent compose
    log("Starting MAS agents via docker compose...", "RUN")
    compose_cmd = "cd /home/mycosoft/mycosoft/mas/docker && docker compose -f docker-compose.agents.yml up -d 2>&1"
    success, output, error = run_cmd(ssh, f"sudo bash -c '{compose_cmd}'", timeout=300)
    
    if error and "error" in error.lower():
        log(f"Compose warning: {error[:200]}", "WARN")
    else:
        log("Agents starting", "OK")
    
    # Step 5: Wait and check status
    log("Waiting for containers to start (10s)...", "RUN")
    time.sleep(10)
    
    log("Checking container status...", "RUN")
    success, output, _ = run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' 2>&1")
    
    # Step 6: Show images
    log("Available images:", "INFO")
    run_cmd(ssh, "sudo docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}' 2>&1 | head -10")
    
    # Step 7: Check agent logs
    log("Checking orchestrator logs (if running)...", "RUN")
    run_cmd(ssh, "sudo docker logs myca-orchestrator 2>&1 | tail -10 || echo 'Not running yet'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MAS STARTUP COMPLETE")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Status: Check container list above

To SSH in:
  ssh mycosoft@192.168.0.188

To check containers:
  sudo docker ps

To view orchestrator logs:
  sudo docker logs -f myca-orchestrator

To restart all agents:
  cd ~/mycosoft/mas/docker
  sudo docker compose -f docker-compose.agents.yml restart
""")
    
    return True

if __name__ == "__main__":
    main()
