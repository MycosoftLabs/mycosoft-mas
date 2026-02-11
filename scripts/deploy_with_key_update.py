#!/usr/bin/env python3
"""
Deploy MAS to VM and update Gemini API key
Requires VM_PASSWORD environment variable
"""
import os
import sys
import time

try:
    import paramiko
except ImportError:
    import subprocess
    print("Installing paramiko...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

# Configuration
MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
GEMINI_KEY = "AIzaSyA1XciZWVlg-P0EI5D3tCQzqHkoW877LoY"
MAS_VM_PASS = os.environ.get("VM_PASSWORD")

if not MAS_VM_PASS:
    # Try to get from user input
    import getpass
    MAS_VM_PASS = getpass.getpass(f"Enter password for {MAS_VM_USER}@{MAS_VM_IP}: ")
    if not MAS_VM_PASS:
        print("ERROR: No password provided.")
        sys.exit(1)

def log(msg, symbol="->"):
    print(f"{symbol} {msg}")

def run_command(ssh, cmd, timeout=120):
    """Execute command and return success, output"""
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        return exit_code == 0, output, error
    except Exception as e:
        return False, "", str(e)

def run_sudo(ssh, cmd, password, timeout=120):
    """Execute command with sudo"""
    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    try:
        stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout, get_pty=True)
        output = stdout.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        return exit_code == 0, output
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("DEPLOY MAS TO VM & UPDATE GEMINI KEY")
    print("=" * 70)
    
    # Connect
    log(f"Connecting to {MAS_VM_IP}...", "[*]")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
        log("Connected successfully", "[+]")
    except Exception as e:
        log(f"Connection failed: {e}", "[X]")
        return False
    
    # Pull latest code
    log("Pulling latest code from GitHub...", "[*]")
    success, output, error = run_command(ssh, 
        "cd ~/mycosoft/mas && git fetch origin && git reset --hard origin/main")
    
    if success or "HEAD is now at" in output:
        log("Code updated to latest", "[+]")
        # Show what commit we're at
        success, commit, _ = run_command(ssh, "cd ~/mycosoft/mas && git log -1 --oneline")
        if commit:
            log(f"  {commit.strip()}", "  ")
    else:
        log(f"Git update had issues: {error[:100]}", "[!]")
    
    # Check current env file location
    log("Checking environment configuration...", "[*]")
    success, output, _ = run_command(ssh, "systemctl show mas-orchestrator | grep EnvironmentFile")
    
    env_file = None
    if "EnvironmentFile" in output:
        # Extract path from EnvironmentFile=path
        for line in output.split('\n'):
            if 'EnvironmentFile=' in line:
                env_file = line.split('=', 1)[1].strip()
                log(f"Found env file: {env_file}", "  ")
                break
    
    if not env_file:
        env_file = "/home/mycosoft/mycosoft/mas/.env"
        log(f"Using default env file: {env_file}", "  ")
    
    # Update or create .env with correct key
    log(f"Setting GEMINI_API_KEY in {env_file}...", "[*]")
    
    # Check if key already exists in file
    success, output, _ = run_command(ssh, f"grep -q GEMINI_API_KEY {env_file} 2>/dev/null && echo exists || echo missing")
    
    if "exists" in output:
        # Update existing key
        cmd = f"sed -i 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY={GEMINI_KEY}/' {env_file}"
        success, _ = run_sudo(ssh, cmd, MAS_VM_PASS)
    else:
        # Append new key
        cmd = f"echo 'GEMINI_API_KEY={GEMINI_KEY}' >> {env_file}"
        success, _ = run_sudo(ssh, cmd, MAS_VM_PASS)
    
    if success:
        log("Gemini API key updated", "[+]")
    else:
        log("Key update may have issues", "[!]")
    
    # Verify key was set
    success, output, _ = run_command(ssh, f"grep GEMINI_API_KEY {env_file}")
    if GEMINI_KEY in output:
        log("Key verified in env file", "[+]")
    
    # Restart orchestrator
    log("Restarting MAS orchestrator...", "[*]")
    success, output = run_sudo(ssh, "systemctl restart mas-orchestrator", MAS_VM_PASS)
    
    if success:
        log("Service restart initiated", "[+]")
    else:
        # Try Docker as fallback
        log("Trying Docker restart...", "[*]")
        run_command(ssh, "docker restart myca-orchestrator-new 2>/dev/null || docker restart myca-orchestrator 2>/dev/null")
    
    # Wait for startup
    log("Waiting for service to start...", "[*]")
    time.sleep(8)
    
    # Check status
    log("Checking service status...", "[*]")
    success, output, _ = run_command(ssh, "systemctl is-active mas-orchestrator 2>/dev/null")
    
    if "active" in output:
        log("Orchestrator is active (systemd)", "[+]")
    else:
        # Check Docker
        success, output, _ = run_command(ssh, "docker ps --filter name=myca-orchestrator --format '{{.Names}}: {{.Status}}'")
        if output.strip():
            log(f"Orchestrator running (Docker): {output.strip()}", "[+]")
        else:
            log("Service status unclear - checking API...", "[!]")
    
    ssh.close()
    
    # Test API
    log("Testing API endpoint...", "[*]")
    import urllib.request
    import json
    
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=10) as resp:
            data = json.loads(resp.read().decode())
            status = data.get('status', 'unknown')
            log(f"API status: {status}", "[+]" if status != "unhealthy" else "[!]")
            
            # Show component status
            if 'components' in data:
                for comp in data['components'][:3]:
                    name = comp.get('name', 'unknown')
                    comp_status = comp.get('status', 'unknown')
                    symbol = "[+]" if comp_status == "healthy" else "[o]"
                    log(f"  {name}: {comp_status}", f"  {symbol}")
    except Exception as e:
        log(f"API test failed: {e}", "[X]")
    
    print("\n" + "=" * 70)
    print("DEPLOYMENT COMPLETE")
    print("=" * 70)
    print(f"""
MAS API: http://{MAS_VM_IP}:8001/health
Docs:    http://{MAS_VM_IP}:8001/docs

Test MYCA with correct key:
  curl -X POST http://{MAS_VM_IP}:8001/api/myca/route \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Are you alive and well?"}}'

View intent classification:
  curl http://{MAS_VM_IP}:8001/api/system/status
""")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDeployment cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
