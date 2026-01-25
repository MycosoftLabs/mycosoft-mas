#!/usr/bin/env python3
"""
Run MYCA Orchestrator directly using the mas-agent image
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
    print("RUNNING MYCA ORCHESTRATOR DIRECTLY")
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
    
    # Step 1: Stop any existing orchestrator
    log("Stopping any existing orchestrator...", "RUN")
    run_cmd(ssh, "sudo docker stop myca-orchestrator 2>/dev/null; sudo docker rm myca-orchestrator 2>/dev/null", show_output=False)
    log("Cleaned up", "OK")
    
    # Step 2: Verify network exists or create one
    log("Setting up Docker network...", "RUN")
    run_cmd(ssh, "sudo docker network create mas-network 2>/dev/null || true", show_output=False)
    
    # Connect redis to network
    run_cmd(ssh, "sudo docker network connect mas-network mas-redis 2>/dev/null || true", show_output=False)
    log("Network ready", "OK")
    
    # Step 3: Run orchestrator container
    log("Starting MYCA Orchestrator container...", "RUN")
    
    orchestrator_cmd = '''docker run -d \\
        --name myca-orchestrator \\
        --restart unless-stopped \\
        --network mas-network \\
        -p 8001:8001 \\
        -e REDIS_URL=redis://mas-redis:6379 \\
        -e POSTGRES_HOST=192.168.0.187 \\
        -e POSTGRES_PORT=5432 \\
        -e POSTGRES_USER=mycosoft \\
        -e POSTGRES_PASSWORD=mycosoft_secure_2026 \\
        -e POSTGRES_DB=mycosoft \\
        -e MAS_API_PORT=8001 \\
        -e PROXMOX_HOST=192.168.0.202 \\
        -e PROXMOX_TOKEN="root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e" \\
        -e LOG_LEVEL=INFO \\
        -v /home/mycosoft/mycosoft/mas:/app/mas:ro \\
        mycosoft/mas-agent:latest \\
        python -m uvicorn core.orchestrator_service:app --host 0.0.0.0 --port 8001
    '''
    
    success, output, error = run_cmd(ssh, f"sudo {orchestrator_cmd}", timeout=60)
    
    if success or (output and len(output) > 10):
        log(f"Container started: {output[:64] if output else 'check status'}", "OK")
    else:
        log(f"Start may have issues: {error[:200] if error else 'unknown'}", "WARN")
    
    # Step 4: Wait and check
    log("Waiting for startup (10s)...", "RUN")
    time.sleep(10)
    
    log("Container status:", "RUN")
    run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    # Step 5: Check logs
    log("Container logs:", "RUN")
    run_cmd(ssh, "sudo docker logs myca-orchestrator 2>&1 | tail -20")
    
    # Step 6: Test API endpoint
    log("Testing API endpoint...", "RUN")
    run_cmd(ssh, "curl -s http://localhost:8001/health 2>&1 | head -5 || echo 'API not responding yet'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MYCA ORCHESTRATOR STATUS")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Orchestrator: Running on port 8001

Dashboard API: http://192.168.0.188:8001/docs
Health Check: http://192.168.0.188:8001/health

To view logs:
  ssh mycosoft@192.168.0.188
  sudo docker logs -f myca-orchestrator
""")
    
    return True

if __name__ == "__main__":
    main()
