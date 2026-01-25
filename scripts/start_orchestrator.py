#!/usr/bin/env python3
"""
Start MYCA Orchestrator on MAS VM
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

def run_cmd(ssh, command, timeout=300, show_output=True):
    """Run command with sudo via bash"""
    if "sudo" in command:
        actual_cmd = command.replace("sudo ", "")
        cmd = f"echo '{MAS_VM_PASS}' | sudo -S bash -c '{actual_cmd}'"
    else:
        cmd = command
    
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    output_lines = [l for l in output.split('\n') if l.strip() and 'password' not in l.lower()]
    
    if show_output and output_lines:
        for line in output_lines[:30]:
            print(f"    {line}")
    
    return exit_code == 0, '\n'.join(output_lines), error

def main():
    print("=" * 60)
    print("STARTING MYCA ORCHESTRATOR")
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
    
    # Step 1: Navigate and check compose file
    log("Checking docker-compose file location...", "RUN")
    success, output, _ = run_cmd(ssh, "ls -la /home/mycosoft/mycosoft/mas/docker/docker-compose.agents.yml", show_output=False)
    if success:
        log("Found docker-compose.agents.yml", "OK")
    else:
        log("Compose file not found!", "ERR")
        return False
    
    # Step 2: Create env file in the docker directory
    log("Creating .env in docker directory...", "RUN")
    env_content = """REDIS_URL=redis://mas-redis:6379
POSTGRES_HOST=192.168.0.187
POSTGRES_PORT=5432
POSTGRES_USER=mycosoft
POSTGRES_PASSWORD=mycosoft_secure_2026
POSTGRES_DB=mycosoft
MAS_API_PORT=8001
PROXMOX_HOST=192.168.0.202
PROXMOX_TOKEN=root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e
UNIFI_USERNAME=cursor_agent
UNIFI_PASSWORD=
ELEVENLABS_API_KEY=
"""
    
    run_cmd(ssh, f"echo '{env_content}' > /home/mycosoft/mycosoft/mas/docker/.env", show_output=False)
    log(".env file created", "OK")
    
    # Step 3: Run docker compose from correct directory
    log("Running docker compose up...", "RUN")
    compose_cmd = "cd /home/mycosoft/mycosoft/mas/docker && docker compose -f docker-compose.agents.yml up -d"
    success, output, error = run_cmd(ssh, f"sudo {compose_cmd}", timeout=300)
    
    # Step 4: Wait and check
    log("Waiting for containers to initialize (15s)...", "RUN")
    time.sleep(15)
    
    log("Container status:", "RUN")
    run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    # Step 5: Check orchestrator logs
    log("Checking orchestrator startup...", "RUN")
    run_cmd(ssh, "sudo docker logs docker-myca-orchestrator-1 2>&1 | tail -15 || sudo docker logs myca-orchestrator 2>&1 | tail -15 || echo 'Container not found'")
    
    # Step 6: Test Redis connectivity
    log("Testing Redis...", "RUN")
    run_cmd(ssh, "sudo docker exec mas-redis redis-cli ping")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("ORCHESTRATOR STATUS")
    print("=" * 60)
    print("""
To monitor:
  ssh mycosoft@192.168.0.188
  sudo docker ps
  sudo docker logs -f docker-myca-orchestrator-1

API (when running):
  http://192.168.0.188:8001/docs
""")
    
    return True

if __name__ == "__main__":
    main()
