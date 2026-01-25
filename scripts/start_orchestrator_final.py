#!/usr/bin/env python3
"""
Start MYCA Orchestrator with Docker socket mounted
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
    print("STARTING MYCA ORCHESTRATOR (with Docker access)")
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
    
    # Step 1: Stop existing
    log("Stopping existing orchestrator...", "RUN")
    run_cmd(ssh, "sudo docker stop myca-orchestrator 2>/dev/null; sudo docker rm myca-orchestrator 2>/dev/null", show_output=False)
    log("Cleaned up", "OK")
    
    # Step 2: Ensure network and connect redis
    run_cmd(ssh, "sudo docker network create mas-network 2>/dev/null || true", show_output=False)
    run_cmd(ssh, "sudo docker network connect mas-network mas-redis 2>/dev/null || true", show_output=False)
    
    # Step 3: Start orchestrator with Docker socket mounted
    log("Starting MYCA Orchestrator with Docker socket...", "RUN")
    
    # Mount Docker socket for container management
    orchestrator_cmd = '''docker run -d \
        --name myca-orchestrator \
        --restart unless-stopped \
        --network mas-network \
        -p 8001:8001 \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /home/mycosoft/mycosoft/mas:/app/mas:ro \
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
    else:
        log(f"Start result: {error[:100] if error else 'check status'}", "WARN")
    
    # Step 4: Wait for startup
    log("Waiting for startup (25s)...", "RUN")
    time.sleep(25)
    
    # Step 5: Check status
    log("Container status:", "RUN")
    run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    # Step 6: Check logs
    log("Orchestrator logs:", "RUN")
    run_cmd(ssh, "sudo docker logs myca-orchestrator 2>&1 | tail -30")
    
    # Step 7: Test API
    log("Testing API health...", "RUN")
    success, output, _ = run_cmd(ssh, "curl -s http://localhost:8001/health 2>&1 | head -5")
    
    if not output or "error" in output.lower():
        log("API may still be starting - check logs manually", "WARN")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("ORCHESTRATOR DEPLOYMENT STATUS")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Services: Redis (6379) + Orchestrator (8001)

API Documentation: http://192.168.0.188:8001/docs
Health Check: http://192.168.0.188:8001/health

Monitor logs:
  ssh mycosoft@192.168.0.188
  sudo docker logs -f myca-orchestrator
""")
    
    return True

if __name__ == "__main__":
    main()
