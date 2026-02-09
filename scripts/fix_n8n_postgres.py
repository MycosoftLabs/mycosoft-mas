#!/usr/bin/env python3
"""
Fix n8n postgres user and restart
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
        print("Fix n8n Postgres User")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Fix the postgres user password
        print("Setting n8n user password in postgres...")
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -c "ALTER USER n8n WITH PASSWORD 'n8npassword';" """)
        
        # Also grant ownership on the database
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -c "ALTER DATABASE n8n OWNER TO n8n;" """)
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -d n8n -c "GRANT ALL ON SCHEMA public TO n8n;" """)
        
        # Restart n8n
        print("\nRestarting n8n...")
        run_command(client, "docker restart myca-n8n")
        
        # Wait
        print("\nWaiting 25 seconds for n8n to start...")
        time.sleep(25)
        
        # Check logs
        print("\nn8n logs:")
        run_command(client, "docker logs myca-n8n --tail 40 2>&1")
        
        # Container status
        print("\n" + "=" * 60)
        print("Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Test n8n endpoint
        print("\n" + "=" * 60)
        print("Testing n8n endpoint")
        print("=" * 60)
        out = run_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:5678 2>/dev/null || echo '000'")
        if out == '200':
            print("\n[SUCCESS] n8n is running!")
            print("Access n8n at: http://192.168.0.187:5678")
        else:
            print(f"\n[PENDING] n8n returned HTTP {out}")
            print("It may still be starting up. Try again in a minute.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
