#!/usr/bin/env python3
"""
Rebuild and restart MAS Docker container on VM 192.168.0.188
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

def run_sudo(ssh, command, password, timeout=600, show_output=True):
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

def main():
    print("=" * 60)
    print("REBUILD MAS CONTAINER ON VM 192.168.0.188")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        log("Connecting to MAS VM...", "RUN")
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
        log("Connected", "OK")
    except Exception as e:
        log(f"Connection failed: {e}", "ERR")
        return False
    
    # Stop current container
    log("Stopping current orchestrator container...", "RUN")
    run_sudo(ssh, "docker stop myca-orchestrator-new 2>/dev/null || docker stop myca-orchestrator 2>/dev/null", 
            MAS_VM_PASS, timeout=60, show_output=False)
    log("Container stopped", "OK")
    
    # Remove old container
    log("Removing old container...", "RUN")
    run_sudo(ssh, "docker rm myca-orchestrator-new 2>/dev/null || docker rm myca-orchestrator 2>/dev/null",
            MAS_VM_PASS, timeout=30, show_output=False)
    log("Old container removed", "OK")
    
    # Build new image
    log("Building new Docker image (this takes 2-5 minutes)...", "RUN")
    success, output = run_sudo(ssh, 
        "bash -c 'cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .' 2>&1 | tail -50",
        MAS_VM_PASS, timeout=600)
    
    if success or "Successfully" in output or "successfully" in output:
        log("Docker image built successfully", "OK")
    else:
        log("Build may have issues, continuing anyway...", "WARN")
    
    # Start new container
    log("Starting new orchestrator container...", "RUN")
    success, output = run_sudo(ssh,
        "docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest 2>&1",
        MAS_VM_PASS, timeout=60)
    
    if success:
        log("Container started", "OK")
    else:
        log(f"Container start issues: {output}", "WARN")
    
    # Wait and check
    log("Waiting for container to start...", "INFO")
    time.sleep(10)
    
    # Check container status
    log("Checking container status...", "RUN")
    success, output = run_sudo(ssh, 
        "docker ps --filter name=myca-orchestrator --format '{{.Names}}: {{.Status}}'",
        MAS_VM_PASS, timeout=30)
    
    ssh.close()
    
    # Test API
    log("Testing API endpoint...", "RUN")
    import urllib.request
    time.sleep(5)  # Extra wait
    
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=15) as resp:
            data = resp.read().decode()
            if "ok" in data.lower():
                log("API responding correctly", "OK")
    except Exception as e:
        log(f"API check: {e}", "WARN")
    
    # Check new endpoint
    log("Testing new /api/code/stats endpoint...", "RUN")
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/api/code/stats", timeout=15) as resp:
            data = resp.read().decode()
            log(f"Code API response: {data[:200]}", "OK")
    except urllib.request.HTTPError as e:
        if e.code == 404:
            log("Code API not found - may need router registration", "WARN")
        else:
            log(f"Code API error: {e}", "WARN")
    except Exception as e:
        log(f"Code API check: {e}", "WARN")
    
    print("\n" + "=" * 60)
    print("REBUILD COMPLETE")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
