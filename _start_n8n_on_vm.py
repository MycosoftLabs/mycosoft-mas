#!/usr/bin/env python3
"""
Start n8n on MAS VM and import workflows
February 4, 2026
"""
import subprocess
import time
import requests
import json
from pathlib import Path

MAS_VM = "192.168.0.188"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
N8N_URL = f"http://{MAS_VM}:5678"

print("=" * 60)
print("Starting n8n on MAS VM (192.168.0.188)")
print("=" * 60)

# Try to install paramiko if not available
try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    subprocess.run(["pip", "install", "paramiko", "-q"], check=True)
    import paramiko

def ssh_execute(commands):
    """Execute commands on the MAS VM via SSH."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\nConnecting to {VM_USER}@{MAS_VM}...")
        client.connect(MAS_VM, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!")
        
        for cmd in commands:
            print(f"\n> {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if output:
                print(output)
            if error:
                print(f"stderr: {error}")
        
        return True
    except Exception as e:
        print(f"SSH Error: {e}")
        return False
    finally:
        client.close()


def check_n8n():
    """Check if n8n is running."""
    try:
        r = requests.get(N8N_URL, timeout=5)
        return r.status_code in [200, 302, 401]
    except:
        return False


def import_workflows_via_api():
    """Import workflows via n8n API."""
    print("\n" + "=" * 60)
    print("Importing workflows to n8n...")
    print("=" * 60)
    
    workflows_dir = Path(r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\n8n\workflows")
    
    # Key workflows to import first
    priority_workflows = [
        "myca_voice_brain.json",
        "01_myca_command_api.json",
        "myca-orchestrator.json",
        "40_personaplex_voice_gateway.json",
    ]
    
    session = requests.Session()
    session.auth = ("morgan@mycosoft.org", "REDACTED_VM_SSH_PASSWORD")
    
    imported = 0
    for wf_name in priority_workflows:
        wf_path = workflows_dir / wf_name
        if not wf_path.exists():
            print(f"[SKIP] {wf_name} not found")
            continue
        
        try:
            with open(wf_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if workflow already exists by name
            workflow_name = data.get("name", wf_path.stem)
            
            # Try to create workflow
            import_data = {
                "name": workflow_name,
                "nodes": data.get("nodes", []),
                "connections": data.get("connections", {}),
                "settings": data.get("settings", {}),
                "active": False
            }
            
            r = session.post(f"{N8N_URL}/api/v1/workflows", json=import_data, timeout=30)
            
            if r.status_code in [200, 201]:
                print(f"[IMPORTED] {workflow_name}")
                imported += 1
            elif r.status_code == 409:
                print(f"[EXISTS] {workflow_name}")
            else:
                print(f"[FAIL] {workflow_name}: {r.status_code}")
                
        except Exception as e:
            print(f"[ERROR] {wf_name}: {e}")
    
    return imported


# Main execution
print("\n[1] Checking current n8n status...")
if check_n8n():
    print("n8n is already running!")
else:
    print("n8n is not running. Starting via SSH...")
    
    commands = [
        "docker ps -a --filter 'name=n8n' --format '{{.Names}}: {{.Status}}'",
        "docker start myca-n8n 2>/dev/null || docker start n8n 2>/dev/null || echo 'Trying docker-compose...'",
        "cd /home/mycosoft/mycosoft/mas && docker-compose -f docker/docker-compose.n8n.yml up -d 2>/dev/null || echo 'docker-compose not available'",
        "sleep 5",
        "docker ps --filter 'name=n8n' --format '{{.Names}}: {{.Status}}'"
    ]
    
    ssh_execute(commands)
    
    # Wait for n8n to start
    print("\nWaiting for n8n to become available...")
    for i in range(30):
        if check_n8n():
            print(f"n8n is now running! (took {i+1}s)")
            break
        time.sleep(1)
    else:
        print("n8n did not start within 30 seconds")

# Import workflows if n8n is running
if check_n8n():
    import_workflows_via_api()
else:
    print("\n[!] n8n is not running. Cannot import workflows.")
    print("    Manual steps:")
    print("    1. SSH to 192.168.0.188")
    print("    2. docker start myca-n8n")
    print("    3. Run this script again")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)
