#!/usr/bin/env python3
"""Debug website static files on VM"""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("="*60)
    print("DEBUGGING WEBSITE STATIC FILES")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Check container status
    print("\n1. WEBSITE CONTAINER STATUS:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker ps --filter name=mycosoft-website --format '{{.Names}} {{.Status}}'")
    print(f"   {out.strip()}")
    
    # Check what's inside the container
    print("\n2. STATIC FILES IN CONTAINER:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls -la /app/.next/static 2>&1 | head -20")
    print(out)
    
    # Check CSS files
    print("\n3. CSS FILES:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls -la /app/.next/static/css 2>&1")
    print(out)
    
    # Check chunks files
    print("\n4. CHUNK FILES:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static/chunks 2>&1 | head -20")
    print(out)
    
    # Try to fetch a static file directly
    print("\n5. TESTING STATIC FILE ACCESS:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static/css/*.css 2>&1")
    css_files = out.strip().split('\n')
    if css_files and css_files[0]:
        css_file = css_files[0].replace('/app/.next/static/', '_next/static/')
        print(f"   Found CSS: {css_file}")
        # Test fetching it via localhost
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' 'http://localhost:3000/{css_file}'")
        code = stdout.read().decode().strip()
        print(f"   HTTP status when fetching: {code}")
    
    # Check what the HTML is requesting vs what exists
    print("\n6. HTML REFERENCES vs ACTUAL FILES:")
    print("-"*40)
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:3000 | grep -o '_next/static/css/[^\"]*' | head -5")
    html_refs = stdout.read().decode().strip().split('\n')
    print(f"   HTML requests these CSS files:")
    for ref in html_refs:
        print(f"      - {ref}")
    
    print(f"\n   Container has these CSS files:")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static/css/ 2>&1")
    for f in out.strip().split('\n'):
        print(f"      - {f}")
    
    # Check container logs for errors
    print("\n7. RECENT CONTAINER LOGS:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker logs mycosoft-website --tail 15 2>&1")
    # Filter out Unicode issues
    for line in out.split('\n')[:15]:
        try:
            print(f"   {line}")
        except:
            print(f"   [log line with encoding issue]")
    
    ssh.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
