#!/usr/bin/env python3
"""
Check postgres configuration and fix n8n
Created: February 4, 2026
"""
import paramiko
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_command(client, cmd, timeout=120):
    """Execute command and return output."""
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    out_safe = out.encode('ascii', errors='replace').decode('ascii')
    err_safe = err.encode('ascii', errors='replace').decode('ascii')
    if out_safe:
        print(out_safe)
    if err_safe:
        print(f"STDERR: {err_safe}")
    return out

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Check Postgres and Fix n8n")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Check postgres environment and users
        print("Checking postgres container environment...")
        run_command(client, "docker exec mycosoft-postgres env | grep -i postgres")
        
        # List postgres users
        print("\nListing postgres users...")
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -c "\\du" """)
        
        # Try with mycosoft user
        print("\nCreating n8n database and user with mycosoft admin...")
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -c "CREATE DATABASE n8n;" 2>/dev/null || echo 'DB exists'""")
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -c "CREATE USER n8n WITH PASSWORD 'n8npassword';" 2>/dev/null || echo 'User exists'""")
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -c "ALTER USER n8n WITH PASSWORD 'n8npassword';" """)
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -c "GRANT ALL PRIVILEGES ON DATABASE n8n TO n8n;" """)
        run_command(client, """docker exec mycosoft-postgres psql -U mycosoft -d n8n -c "GRANT ALL ON SCHEMA public TO n8n;" """)
        
        # Restart n8n
        print("\nRestarting n8n...")
        run_command(client, "docker restart myca-n8n")
        
        print("\nWaiting 25 seconds...")
        time.sleep(25)
        
        # Check logs
        print("\nn8n logs:")
        run_command(client, "docker logs myca-n8n --tail 20 2>&1")
        
        # Test endpoint
        print("\n" + "=" * 60)
        print("Testing n8n")
        print("=" * 60)
        out = run_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:5678 2>/dev/null || echo '000'")
        if out == '200':
            print("\n[SUCCESS] n8n is running at http://192.168.0.187:5678")
        else:
            print(f"\n[PENDING] HTTP {out} - may need more time")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
