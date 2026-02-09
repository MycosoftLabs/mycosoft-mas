#!/usr/bin/env python3
"""
Verify all services are running
Created: February 4, 2026
"""
import paramiko
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_command(client, cmd, timeout=60):
    """Execute command and return output."""
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    out_safe = out.encode('ascii', errors='replace').decode('ascii')
    if out_safe:
        print(out_safe)
    return out, err

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Service Verification")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Check n8n logs
        print("n8n logs:")
        run_command(client, "docker logs myca-n8n --tail 50 2>&1")
        
        # Container status
        print("\n" + "=" * 60)
        print("Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Test endpoints
        print("\n" + "=" * 60)
        print("Endpoint Tests")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("Mycorrhizae API", "http://localhost:8002/health"),
            ("n8n", "http://localhost:5678"),
            ("n8n healthz", "http://localhost:5678/healthz"),
        ]
        
        all_ok = True
        for name, url in endpoints:
            out, _ = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo '000'")
            ok = out in ['200', '301', '302']
            status = "[OK]" if ok else "[--]"
            print(f"  {status} {name}: HTTP {out}")
            if not ok and 'n8n' in name.lower():
                all_ok = False
        
        print("\n" + "=" * 60)
        if all_ok:
            print("All services are running!")
        else:
            print("Some services still starting - check again in a minute")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
