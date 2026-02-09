#!/usr/bin/env python3
"""
Fix n8n connection - use localhost for postgres
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
        print("Fix n8n - Use localhost for postgres")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Stop and remove old n8n
        print("Stopping old n8n container...")
        run_command(client, "docker stop myca-n8n 2>/dev/null || true")
        run_command(client, "docker rm myca-n8n 2>/dev/null || true")
        
        # Start n8n with localhost for postgres (since we use --network host)
        print("\nStarting n8n with localhost postgres connection...")
        n8n_cmd = """docker run -d --name myca-n8n \
            -e DB_TYPE=postgresdb \
            -e DB_POSTGRESDB_HOST=localhost \
            -e DB_POSTGRESDB_PORT=5432 \
            -e DB_POSTGRESDB_DATABASE=n8n \
            -e DB_POSTGRESDB_USER=n8n \
            -e DB_POSTGRESDB_PASSWORD=n8npassword \
            -e N8N_BASIC_AUTH_ACTIVE=false \
            -e WEBHOOK_URL=http://192.168.0.187:5678/ \
            -e N8N_HOST=0.0.0.0 \
            -e N8N_PORT=5678 \
            -v n8n_data:/home/node/.n8n \
            --network host \
            --restart unless-stopped \
            n8nio/n8n:latest"""
        run_command(client, n8n_cmd)
        
        # Wait for startup
        print("\nWaiting 20 seconds for n8n to start...")
        time.sleep(20)
        
        # Check logs
        print("\nn8n logs:")
        run_command(client, "docker logs myca-n8n --tail 30 2>&1")
        
        # Container status
        print("\n" + "=" * 60)
        print("Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Test endpoints
        print("\n" + "=" * 60)
        print("Testing Endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("Mycorrhizae API", "http://localhost:8002/health"),
            ("n8n", "http://localhost:5678"),
        ]
        
        for name, url in endpoints:
            out = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo '000'")
            status = "[OK]" if out in ['200', '301', '302'] else "[--]"
            print(f"  {status} {name}: HTTP {out}")
        
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
        print("\nAccess n8n at: http://192.168.0.187:5678")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
