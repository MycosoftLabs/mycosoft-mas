#!/usr/bin/env python3
"""
Quick Deploy MAS to VM 192.168.0.188
Pulls latest code and restarts orchestrator service
"""
import sys
import time

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

def run_command(ssh, command, timeout=300, show_output=True):
    """Run command on remote"""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    exit_code = stdout.channel.recv_exit_status()
    
    if show_output and output:
        for line in output.strip().split('\n')[:30]:
            print(f"    {line}")
    
    return exit_code == 0, output, error

def run_sudo(ssh, command, password, timeout=300, show_output=True):
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
            if show_output and len(output_lines) <= 20:
                print(f"    {line}")
    
    exit_code = stdout.channel.recv_exit_status()
    return exit_code == 0, '\n'.join(output_lines)

def main():
    print("=" * 60)
    print("QUICK DEPLOY MAS TO VM 192.168.0.188")
    print("=" * 60)
    
    # Connect
    log("Connecting to MAS VM...", "RUN")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
        log("Connected", "OK")
    except Exception as e:
        log(f"Connection failed: {e}", "ERR")
        return False
    
    # Pull latest code
    log("Pulling latest code from GitHub...", "RUN")
    success, output, error = run_command(ssh, 
        "cd ~/mycosoft/mas && git fetch origin && git reset --hard origin/main 2>&1", 
        timeout=120)
    
    if success or "HEAD is now at" in output:
        log("Code updated", "OK")
    else:
        log(f"Git pull may have issues: {error}", "WARN")
    
    # Restart orchestrator service
    log("Restarting MAS orchestrator service...", "RUN")
    success, output = run_sudo(ssh, "systemctl restart mas-orchestrator", MAS_VM_PASS, timeout=30)
    
    if success:
        log("Orchestrator service restarted", "OK")
    else:
        log("Service restart may have issues", "WARN")
        # Try Docker alternative
        log("Trying Docker restart...", "RUN")
        run_sudo(ssh, "docker restart myca-orchestrator-new 2>&1 || docker restart myca-orchestrator 2>&1", 
                MAS_VM_PASS, timeout=60, show_output=False)
    
    # Wait for service to start
    log("Waiting for service to start...", "INFO")
    time.sleep(5)
    
    # Check service status
    log("Checking orchestrator status...", "RUN")
    success, output, _ = run_command(ssh, "systemctl is-active mas-orchestrator 2>&1 || echo checking-docker")
    
    if "active" in output:
        log("Orchestrator running via systemd", "OK")
    else:
        # Check Docker
        success, output, _ = run_command(ssh, "docker ps --filter name=myca-orchestrator --format '{{.Names}}: {{.Status}}'")
        if output.strip():
            log(f"Orchestrator running via Docker: {output.strip()}", "OK")
        else:
            log("Orchestrator status unclear - check manually", "WARN")
    
    ssh.close()
    
    # Test API
    log("Testing API endpoint...", "RUN")
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=10) as resp:
            data = resp.read().decode()
            if "ok" in data.lower() or "healthy" in data.lower():
                log("API responding correctly", "OK")
            else:
                log(f"API response: {data[:100]}", "INFO")
    except Exception as e:
        log(f"API check failed: {e}", "WARN")
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"""
MAS VM: {MAS_VM_IP}
API: http://{MAS_VM_IP}:8001/health
Docs: http://{MAS_VM_IP}:8001/docs

To verify new endpoints:
  curl http://{MAS_VM_IP}:8001/api/code/stats
""")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
