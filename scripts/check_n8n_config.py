#!/usr/bin/env python3
"""Check n8n container configuration"""
import os
import shlex

import paramiko

def main():
    vm_pass = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not vm_pass:
        raise SystemExit("Set VM_PASSWORD or VM_SSH_PASSWORD (from .credentials.local)")
    n8n_basic = os.environ.get("N8N_BASIC_AUTH_PASSWORD", "")
    if not n8n_basic:
        raise SystemExit("Set N8N_BASIC_AUTH_PASSWORD for API curl test")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=vm_pass)
    
    print('=== n8n Container Environment ===')
    stdin, stdout, stderr = ssh.exec_command('docker exec myca-n8n env | grep -E "N8N|BASIC" | sort')
    print(stdout.read().decode())
    
    print('=== n8n Container Logs (last 20 lines) ===')
    stdin, stdout, stderr = ssh.exec_command('docker logs myca-n8n 2>&1 | tail -20')
    print(stdout.read().decode())
    
    print('=== Testing n8n health ===')
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:5678/healthz')
    print(stdout.read().decode())
    
    # Test with basic auth
    print('\n=== Testing n8n API with Basic Auth ===')
    pw_q = shlex.quote(n8n_basic)
    stdin, stdout, stderr = ssh.exec_command(
        f"export N8N_BASIC_AUTH_PASSWORD={pw_q}; "
        f"curl -s -u admin:$N8N_BASIC_AUTH_PASSWORD "
        f"http://localhost:5678/api/v1/workflows | head -100"
    )
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
