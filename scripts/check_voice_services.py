#!/usr/bin/env python3
"""Check voice services on MAS VM"""

import paramiko

MAS_HOST = "192.168.0.188"
MAS_USER = "mycosoft"
MAS_PASS = "REDACTED_VM_SSH_PASSWORD"

def run_command(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

def main():
    print(f"Connecting to MAS VM at {MAS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(MAS_HOST, username=MAS_USER, password=MAS_PASS)
    
    print("\n=== All Containers (voice/whisper/speech/myca) ===")
    out, _ = run_command(ssh, 'docker ps -a | grep -iE "voice|whisper|speech|myca"')
    print(out if out else "None found")
    
    print("\n=== Voice Ports (8000, 5500, 8765, 8090) ===")
    out, _ = run_command(ssh, 'ss -tlnp | grep -E ":8000|:5500|:8765|:8090"')
    print(out if out else "None listening")
    
    print("\n=== Checking orchestrator endpoints ===")
    out, _ = run_command(ssh, 'curl -s http://localhost:8001/health 2>/dev/null')
    print(f"Health: {out}")
    
    out, _ = run_command(ssh, 'curl -s -X POST http://localhost:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d \'{"message":"hello"}\' 2>/dev/null')
    print(f"Voice Chat: {out[:200] if out else 'No response'}")
    
    ssh.close()

if __name__ == "__main__":
    main()
