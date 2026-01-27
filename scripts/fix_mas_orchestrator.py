#!/usr/bin/env python3
"""Fix and restart MAS orchestrator backend"""

import paramiko
import time
import requests

MAS_HOST = "192.168.0.188"
MAS_USER = "mycosoft"
MAS_PASS = "Mushroom1!Mushroom1!"

def run_command(ssh, cmd, sudo=False):
    """Run a command and return output"""
    if sudo:
        cmd = f"echo '{MAS_PASS}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

def main():
    print(f"Connecting to MAS VM at {MAS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(MAS_HOST, username=MAS_USER, password=MAS_PASS)
        print("Connected!")
        
        # Check orchestrator health
        print("\n=== Checking Orchestrator Health ===")
        out, err = run_command(ssh, 'docker inspect myca-orchestrator --format "{{.State.Health.Status}}"')
        print(f"Health Status: {out.strip()}")
        
        # Check logs
        print("\n=== Recent Orchestrator Logs ===")
        out, err = run_command(ssh, 'docker logs myca-orchestrator --tail 30 2>&1')
        print(out)
        
        # Try to hit the API directly
        print("\n=== Testing API Endpoint ===")
        try:
            response = requests.get(f"http://{MAS_HOST}:8001/health", timeout=5)
            print(f"API Response: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            print(f"API Error: {e}")
        
        # Restart the orchestrator if unhealthy
        print("\n=== Restarting Orchestrator Container ===")
        out, err = run_command(ssh, 'docker restart myca-orchestrator', sudo=True)
        print(f"Restart output: {out}")
        if err and "password" not in err.lower():
            print(f"Restart error: {err}")
        
        # Wait for it to come up
        print("Waiting 10 seconds for container to start...")
        time.sleep(10)
        
        # Check health again
        print("\n=== Checking Health After Restart ===")
        out, err = run_command(ssh, 'docker inspect myca-orchestrator --format "{{.State.Health.Status}}"')
        print(f"Health Status: {out.strip()}")
        
        # Check if API is responding
        print("\n=== Testing API After Restart ===")
        try:
            response = requests.get(f"http://{MAS_HOST}:8001/health", timeout=10)
            print(f"API Response: {response.status_code}")
            print(response.text[:500])
        except Exception as e:
            print(f"API Error: {e}")
        
        # Also test the /agents endpoint
        print("\n=== Testing /agents Endpoint ===")
        try:
            response = requests.get(f"http://{MAS_HOST}:8001/agents", timeout=10)
            print(f"Agents Response: {response.status_code}")
            if response.ok:
                data = response.json()
                print(f"Found {len(data) if isinstance(data, list) else 'N/A'} agents")
        except Exception as e:
            print(f"Agents Error: {e}")
        
        ssh.close()
        print("\n=== Done ===")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
