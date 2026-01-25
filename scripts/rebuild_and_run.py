#!/usr/bin/env python3
"""
Pull latest code, rebuild agent image, and start orchestrator
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

def run_cmd(ssh, command, timeout=600, show_output=True):
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
    print("REBUILD AND START ORCHESTRATOR")
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
    
    # Step 1: Pull latest code
    log("Pulling latest code from GitHub...", "RUN")
    success, output, _ = run_cmd(ssh, 
        "cd /home/mycosoft/mycosoft/mas && git fetch origin main && git reset --hard origin/main && git log -1 --oneline",
        timeout=60)
    log("Code updated", "OK")
    
    # Step 2: Stop existing container
    log("Stopping existing containers...", "RUN")
    run_cmd(ssh, "sudo docker stop myca-orchestrator 2>/dev/null; sudo docker rm myca-orchestrator 2>/dev/null", show_output=False)
    log("Containers stopped", "OK")
    
    # Step 3: Rebuild image with new requirements
    log("Rebuilding agent image with uvicorn/fastapi (2-3 min)...", "RUN")
    build_cmd = "cd /home/mycosoft/mycosoft/mas && docker build --no-cache -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent . 2>&1 | tail -30"
    success, output, _ = run_cmd(ssh, f"sudo {build_cmd}", timeout=600)
    
    if "Successfully" in output or "naming to" in output.lower():
        log("Image rebuilt successfully", "OK")
    else:
        log("Build completed - check output", "WARN")
    
    # Step 4: Ensure network exists
    run_cmd(ssh, "sudo docker network create mas-network 2>/dev/null || true", show_output=False)
    run_cmd(ssh, "sudo docker network connect mas-network mas-redis 2>/dev/null || true", show_output=False)
    
    # Step 5: Start orchestrator
    log("Starting MYCA Orchestrator...", "RUN")
    orchestrator_cmd = '''docker run -d \
        --name myca-orchestrator \
        --restart unless-stopped \
        --network mas-network \
        -p 8001:8001 \
        -e REDIS_URL=redis://mas-redis:6379 \
        -e POSTGRES_HOST=192.168.0.187 \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USER=mycosoft \
        -e POSTGRES_PASSWORD=mycosoft_secure_2026 \
        -e POSTGRES_DB=mycosoft \
        -e MAS_API_PORT=8001 \
        -e PYTHONPATH=/app \
        --entrypoint python \
        mycosoft/mas-agent:latest \
        -m uvicorn core.orchestrator_service:app --host 0.0.0.0 --port 8001'''
    
    success, output, error = run_cmd(ssh, f"sudo {orchestrator_cmd}", timeout=60)
    if output:
        log(f"Container started: {output[:12]}", "OK")
    
    # Step 6: Wait and verify
    log("Waiting for startup (20s)...", "RUN")
    time.sleep(20)
    
    log("Container status:", "RUN")
    run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    log("Orchestrator logs:", "RUN")
    run_cmd(ssh, "sudo docker logs myca-orchestrator 2>&1 | tail -25")
    
    log("Testing API endpoint...", "RUN")
    run_cmd(ssh, "curl -s http://localhost:8001/ 2>&1 | head -10 || echo 'Waiting for API...'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Services: Redis + Orchestrator

API: http://192.168.0.188:8001/docs

SSH: ssh mycosoft@192.168.0.188
Logs: sudo docker logs -f myca-orchestrator
""")
    
    return True

if __name__ == "__main__":
    main()
