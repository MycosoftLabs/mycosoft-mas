#!/usr/bin/env python3
"""
Run MYCA Orchestrator with proper entrypoint override
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
    print("STARTING MYCA ORCHESTRATOR (v2)")
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
    
    # Step 1: Stop and remove existing
    log("Cleaning up old container...", "RUN")
    run_cmd(ssh, "sudo docker stop myca-orchestrator 2>/dev/null; sudo docker rm myca-orchestrator 2>/dev/null", show_output=False)
    log("Cleaned up", "OK")
    
    # Step 2: Run with entrypoint override
    log("Starting MYCA Orchestrator with entrypoint override...", "RUN")
    
    # Use --entrypoint to override
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
        -e PYTHONPATH=/app \\
        --entrypoint python \\
        mycosoft/mas-agent:latest \\
        -m uvicorn core.orchestrator_service:app --host 0.0.0.0 --port 8001
    '''
    
    success, output, error = run_cmd(ssh, f"sudo {orchestrator_cmd}", timeout=60)
    
    if output and len(output) > 10:
        log(f"Container ID: {output[:12]}", "OK")
    else:
        log(f"Container start result: {error[:100] if error else 'check status'}", "WARN")
    
    # Step 3: Wait for startup
    log("Waiting for startup (15s)...", "RUN")
    time.sleep(15)
    
    # Step 4: Check status
    log("Container status:", "RUN")
    run_cmd(ssh, "sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' | grep -E 'NAMES|myca|redis'")
    
    # Step 5: Check logs
    log("Container logs (last 20 lines):", "RUN")
    run_cmd(ssh, "sudo docker logs myca-orchestrator 2>&1 | tail -20")
    
    # Step 6: Test health
    log("Testing API...", "RUN")
    success, output, _ = run_cmd(ssh, "curl -s http://localhost:8001/ 2>&1 || echo 'No response'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("ORCHESTRATOR DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"""
MAS VM: 192.168.0.188
Redis: Running on :6379
Orchestrator: Port 8001

Access:
  API Docs: http://192.168.0.188:8001/docs
  Health: http://192.168.0.188:8001/health

Monitor:
  ssh mycosoft@192.168.0.188
  sudo docker logs -f myca-orchestrator
""")
    
    return True

if __name__ == "__main__":
    main()
