#!/usr/bin/env python3
"""
Deploy Voice/Brain API to Sandbox VM
Created: February 5, 2026
"""
import paramiko
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_ssh_command(client, cmd, timeout=120):
    """Execute SSH command and return output."""
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        print(out[:2000])
    if err and "warning" not in err.lower():
        print(f"STDERR: {err[:500]}")
    return out

def main():
    print("=" * 70)
    print("Deploying Voice/Brain API to Sandbox")
    print("=" * 70)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("SSH Connected\n")
        
        # 1. Pull latest code
        print("\n" + "=" * 50)
        print("1. Pulling latest code...")
        print("=" * 50)
        
        commands = [
            "cd /home/mycosoft/mycosoft/mas && git fetch origin",
            "cd /home/mycosoft/mycosoft/mas && git reset --hard origin/main",
            "cd /home/mycosoft/mycosoft/mas && git log --oneline -3"
        ]
        
        for cmd in commands:
            run_ssh_command(client, cmd)
        
        # 2. Check MINDEX container details
        print("\n" + "=" * 50)
        print("2. Checking MINDEX container...")
        print("=" * 50)
        
        run_ssh_command(client, "docker ps -a --filter 'name=mindex' --format '{{.Names}}: {{.Status}}'")
        
        # 3. Find where MINDEX is defined and rebuild
        print("\n" + "=" * 50)
        print("3. Rebuilding MINDEX API container...")
        print("=" * 50)
        
        # Check if there's a dockerfile for mindex
        run_ssh_command(client, "ls -la /home/mycosoft/mycosoft/mas/services/mindex/")
        
        # Find compose file with mindex
        run_ssh_command(client, "grep -l 'mindex' /opt/mycosoft/*.yml 2>/dev/null || echo 'Not in /opt/mycosoft'")
        run_ssh_command(client, "grep -l 'mindex' /home/mycosoft/mycosoft/mas/*.yml 2>/dev/null || echo 'Checking compose files...'")
        
        # Check docker-compose files in mas directory
        run_ssh_command(client, "ls -la /home/mycosoft/mycosoft/mas/docker*.yml 2>/dev/null | head -5")
        
        # 4. Restart MINDEX container with latest code
        print("\n" + "=" * 50)
        print("4. Restarting MINDEX container...")
        print("=" * 50)
        
        # Stop existing container
        run_ssh_command(client, "docker stop mindex-api 2>/dev/null || echo 'Already stopped'")
        run_ssh_command(client, "docker rm mindex-api 2>/dev/null || echo 'Already removed'")
        
        # Start new container with volume mount to get latest code
        mindex_start_cmd = """docker run -d --name mindex-api \
            --network host \
            -v /home/mycosoft/mycosoft/mas/services/mindex:/app:ro \
            -e MINDEX_PORT=8000 \
            -w /app \
            --restart unless-stopped \
            python:3.11-slim sh -c "pip install fastapi uvicorn httpx pydantic && python api.py"
        """
        run_ssh_command(client, mindex_start_cmd)
        
        # Wait for startup
        print("\nWaiting 15 seconds for container to start...")
        time.sleep(15)
        
        # 5. Check container status
        print("\n" + "=" * 50)
        print("5. Checking container status...")
        print("=" * 50)
        
        run_ssh_command(client, "docker ps --filter 'name=mindex-api' --format '{{.Names}}: {{.Status}}'")
        run_ssh_command(client, "docker logs mindex-api --tail 20 2>&1")
        
        # 6. Test new endpoints
        print("\n" + "=" * 50)
        print("6. Testing new Voice/Brain endpoints...")
        print("=" * 50)
        
        time.sleep(5)  # Extra wait for API to be ready
        
        test_endpoints = [
            ("Root", "curl -s http://localhost:8000/"),
            ("Health", "curl -s http://localhost:8000/health"),
            ("Voice Tools", "curl -s http://localhost:8000/api/voice/tools"),
            ("Brain Status", "curl -s http://localhost:8000/api/brain/status"),
        ]
        
        for name, cmd in test_endpoints:
            print(f"\n  Testing {name}:")
            run_ssh_command(client, cmd)
        
        # 7. Summary
        print("\n" + "=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print("""
New Voice/Brain API endpoints available:
  - http://192.168.0.187:8000/api/voice/tools
  - http://192.168.0.187:8000/api/voice/execute
  - http://192.168.0.187:8000/api/brain/status
  - http://192.168.0.187:8000/api/brain/query

Browser Test URLs:
  - http://192.168.0.187:8000/docs (Full API documentation)
  - https://sandbox.mycosoft.com (Main website)
        """)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
