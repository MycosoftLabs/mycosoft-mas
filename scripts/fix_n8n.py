#!/usr/bin/env python3
"""
Fix n8n and complete deployment
Created: February 4, 2026
"""
import paramiko
import sys
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
    exit_code = stdout.channel.recv_exit_status()
    out_safe = out.encode('ascii', errors='replace').decode('ascii')
    err_safe = err.encode('ascii', errors='replace').decode('ascii')
    if out_safe:
        print(out_safe)
    if err_safe:
        print(f"STDERR: {err_safe}")
    return out, err, exit_code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Fix n8n Deployment")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Step 1: Check n8n postgres logs
        print("=" * 60)
        print("Step 1: Check n8n-postgres logs")
        print("=" * 60)
        run_command(client, "docker logs myca-n8n-postgres --tail 20 2>&1")
        
        # Step 2: Try connecting n8n to existing postgres
        print("\n" + "=" * 60)
        print("Step 2: Reconfigure n8n to use existing postgres")
        print("=" * 60)
        
        # Stop and remove the problematic containers
        run_command(client, "docker stop myca-n8n myca-n8n-postgres myca-n8n-redis 2>/dev/null || true")
        run_command(client, "docker rm myca-n8n myca-n8n-postgres myca-n8n-redis 2>/dev/null || true")
        
        # Create n8n database in existing postgres
        print("\nCreating n8n database in existing postgres...")
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -c "CREATE DATABASE n8n;" 2>/dev/null || echo 'Database may already exist'""")
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -c "CREATE USER n8n WITH PASSWORD 'n8npassword';" 2>/dev/null || echo 'User may already exist'""")
        run_command(client, """docker exec mycosoft-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE n8n TO n8n;" 2>/dev/null || true""")
        
        # Step 3: Start n8n connecting to existing postgres
        print("\n" + "=" * 60)
        print("Step 3: Start n8n with existing postgres")
        print("=" * 60)
        
        n8n_run_cmd = """docker run -d --name myca-n8n \
            -p 5678:5678 \
            -e DB_TYPE=postgresdb \
            -e DB_POSTGRESDB_HOST=mycosoft-postgres \
            -e DB_POSTGRESDB_PORT=5432 \
            -e DB_POSTGRESDB_DATABASE=n8n \
            -e DB_POSTGRESDB_USER=n8n \
            -e DB_POSTGRESDB_PASSWORD=n8npassword \
            -e N8N_BASIC_AUTH_ACTIVE=false \
            -e WEBHOOK_URL=http://192.168.0.187:5678/ \
            -v n8n_data:/home/node/.n8n \
            --network host \
            --restart unless-stopped \
            n8nio/n8n:latest"""
        
        run_command(client, n8n_run_cmd, timeout=60)
        
        # Wait for n8n to start
        print("\nWaiting for n8n to start...")
        time.sleep(10)
        
        # Step 4: Check n8n status
        print("\n" + "=" * 60)
        print("Step 4: Check n8n status")
        print("=" * 60)
        run_command(client, "docker logs myca-n8n --tail 30 2>&1")
        
        # Step 5: Final status
        print("\n" + "=" * 60)
        print("Step 5: Final container status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Step 6: Test endpoints
        print("\n" + "=" * 60)
        print("Step 6: Testing all endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("Mycorrhizae API", "http://localhost:8002/health"),
            ("n8n", "http://localhost:5678"),
        ]
        
        for name, url in endpoints:
            out, _, _ = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo 'FAIL'")
            status = "[OK]" if out in ['200', '301', '302'] else "[NOT OK]"
            print(f"  {status} {name}: HTTP {out}")
        
        print("\n" + "=" * 60)
        print("Deployment Complete!")
        print("=" * 60)
        print("\nAccess n8n at: http://192.168.0.187:5678")
        print("Website: https://sandbox.mycosoft.com")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
