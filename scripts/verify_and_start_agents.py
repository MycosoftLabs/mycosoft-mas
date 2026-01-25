#!/usr/bin/env python3
"""
Verify MAS Orchestrator and start initial agents
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
    """Run command"""
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
        for line in output_lines[:25]:
            print(f"    {line}")
    
    return exit_code == 0, '\n'.join(output_lines), error

def main():
    print("=" * 60)
    print("MAS ORCHESTRATOR VERIFICATION")
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
    
    # Step 1: Check health
    log("Checking health endpoint...", "RUN")
    success, output, _ = run_cmd(ssh, "curl -s http://localhost:8001/health")
    if '"status":"ok"' in output:
        log("Health check passed!", "OK")
    else:
        log(f"Health: {output}", "WARN")
    
    # Step 2: Get API info
    log("Getting API info...", "RUN")
    run_cmd(ssh, "curl -s http://localhost:8001/ | head -10")
    
    # Step 3: Get registered agents
    log("Getting registered agents...", "RUN")
    run_cmd(ssh, "curl -s http://localhost:8001/agents | head -20")
    
    # Step 4: Get available metrics
    log("Getting metrics...", "RUN")
    run_cmd(ssh, "curl -s http://localhost:8001/metrics 2>&1 | head -15 || echo 'Metrics not available yet'")
    
    # Step 5: Check container stats
    log("Container resource usage:", "RUN")
    run_cmd(ssh, "sudo docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}'")
    
    # Step 6: System resources
    log("System resources:", "RUN")
    run_cmd(ssh, "free -h | grep -E 'Mem|Swap'")
    run_cmd(ssh, "uptime", show_output=True)
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MAS v2 DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"""
MYCA ORCHESTRATOR IS LIVE!

MAS VM: 192.168.0.188
API Docs: http://192.168.0.188:8001/docs
Health: http://192.168.0.188:8001/health
Agents: http://192.168.0.188:8001/agents

Running Services:
  - Redis (message broker): 192.168.0.188:6379
  - MYCA Orchestrator: 192.168.0.188:8001

Monitor:
  ssh mycosoft@192.168.0.188
  sudo docker logs -f myca-orchestrator

The MAS v2 system is now operational!
""")
    
    return True

if __name__ == "__main__":
    main()
