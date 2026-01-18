#!/usr/bin/env python3
"""Test static file access on VM"""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")
    
    # Test direct access to CSS files
    test_urls = [
        "http://localhost:3000",
        "http://localhost:3000/_next/static/css/40f35a41b2e2f0e8.css",
        "http://localhost:3000/_next/static/css/5160586124011305.css",
        "http://localhost:3000/_next/static/chunks/main-app-2e5788c1099c469f.js",
    ]
    
    print("\nTesting direct localhost access on VM:")
    print("-" * 50)
    
    for url in test_urls:
        stdin, stdout, stderr = ssh.exec_command(
            f"curl -s -o /dev/null -w '%{{http_code}} %{{size_download}}' '{url}'"
        )
        result = stdout.read().decode().strip()
        print(f"  {url.split('localhost:3000')[1] or '/'}: {result}")
    
    # Check if there's a mismatch between the fresh build and old HTML
    print("\n\nChecking build ID mismatch:")
    print("-" * 50)
    
    # Get build ID from HTML
    stdin, stdout, stderr = ssh.exec_command(
        "curl -s http://localhost:3000 | grep -o 'gtir2foz1RAwHs2_CVzWT\\|[a-zA-Z0-9_-]\\{21\\}' | head -1"
    )
    html_build = stdout.read().decode().strip()
    print(f"  Build ID in HTML: {html_build}")
    
    # Get build ID from filesystem
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker exec mycosoft-website ls /app/.next/static | grep -v chunks | grep -v css | grep -v media"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    fs_build = stdout.read().decode().strip()
    print(f"  Build ID in container: {fs_build}")
    
    # Check the actual chunk files that are requested vs exist
    print("\n\nJS chunks comparison:")
    print("-" * 50)
    
    # Get requested chunks from HTML
    stdin, stdout, stderr = ssh.exec_command(
        "curl -s http://localhost:3000 | grep -oE 'chunks/[^\"]+\\.js' | head -5"
    )
    requested = stdout.read().decode().strip().split('\n')
    print("  Requested in HTML:")
    for r in requested:
        print(f"    - {r}")
    
    # Check if they exist
    print("\n  Testing if they exist:")
    for chunk in requested[:3]:
        if chunk:
            chunk_path = f"/_next/static/{chunk}"
            stdin, stdout, stderr = ssh.exec_command(
                f"curl -s -o /dev/null -w '%{{http_code}}' 'http://localhost:3000{chunk_path}'"
            )
            code = stdout.read().decode().strip()
            print(f"    {chunk}: {code}")
    
    ssh.close()

if __name__ == "__main__":
    main()
