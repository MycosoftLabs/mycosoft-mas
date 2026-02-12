#!/usr/bin/env python3
"""Rebuild and restart MAS on VM 188 - reads API keys from environment"""

import paramiko
import time
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM = os.environ.get("MAS_VM_IP", "192.168.0.188")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)

# Load API keys from environment
API_KEYS = {
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    "XAI_API_KEY": os.environ.get("XAI_API_KEY", ""),
}


def run_cmd(client, cmd, timeout=300, show_lines=50):
    """Run command and show output"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    
    lines = out.strip().split('\n')
    if len(lines) > show_lines:
        print(f"... ({len(lines) - show_lines} lines hidden) ...")
        for line in lines[-show_lines:]:
            print(line)
    else:
        print(out)
    
    if err.strip():
        print(f"STDERR: {err[:500]}")
    
    return stdout.channel.recv_exit_status()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to MAS VM ({VM})...")
        client.connect(VM, username=USER, password=PASS, timeout=30)
        
        # Pull latest
        print("\n[1/4] Pulling latest code...")
        run_cmd(client, "cd /home/mycosoft/mycosoft/mas && git fetch && git reset --hard origin/main && git log -1 --oneline")
        
        # Stop container
        print("\n[2/4] Stopping container...")
        run_cmd(client, "docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null; echo 'Stopped'")
        
        # Build
        print("\n[3/4] Building Docker image (this takes a few minutes)...")
        exit_code = run_cmd(client, "cd /home/mycosoft/mycosoft/mas && docker build --no-cache -t mycosoft/mas-agent:latest . 2>&1", timeout=600)
        
        if exit_code != 0:
            print(f"Build may have issues (exit {exit_code}), checking image...")
            run_cmd(client, "docker images mycosoft/mas-agent:latest --format '{{.ID}} {{.CreatedAt}}'")
        
        # Build docker run command with env vars
        env_flags = []
        for key, val in API_KEYS.items():
            if val:
                env_flags.append(f'-e {key}="{val}"')
        env_str = " ".join(env_flags)
        
        # Start container
        print("\n[4/4] Starting container...")
        docker_cmd = f"""docker run -d --name myca-orchestrator-new \\
            --restart unless-stopped \\
            --network host \\
            -e MAS_API_PORT=8000 \\
            -e MINDEX_API_URL=http://192.168.0.189:8000 \\
            -e REDIS_URL=redis://192.168.0.189:6379/0 \\
            {env_str} \\
            mycosoft/mas-agent:latest"""
        run_cmd(client, docker_cmd)
        
        # Wait
        print("\nWaiting for startup...")
        time.sleep(15)
        
        # Health check
        print("\n[+] Health check:")
        run_cmd(client, "curl -s http://127.0.0.1:8000/health")
        
        # Test ping
        print("\n[+] Testing /api/myca/ping:")
        run_cmd(client, "curl -s http://127.0.0.1:8000/api/myca/ping")
        
        # Test chat-simple
        print("\n[+] Testing /api/myca/chat-simple:")
        run_cmd(client, 'curl -s -X POST http://127.0.0.1:8000/api/myca/chat-simple -H "Content-Type: application/json" -d \'{"message": "Are you alive?"}\'')
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()
