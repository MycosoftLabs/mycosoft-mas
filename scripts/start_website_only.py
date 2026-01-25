#!/usr/bin/env python3
"""
Start just the website container using docker run.
"""

import paramiko
import time
import sys

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "→", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "STEP": "▶"}
    print(f"[{ts}] {symbols.get(level, '→')} {msg}")

def run_ssh(ssh, cmd, timeout=120):
    """Run SSH command and return output."""
    log(f"Running: {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='replace')
    error = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if error and exit_code != 0:
        log(f"Stderr: {error[:300]}", "WARN")
    return output.strip(), error.strip(), exit_code

def main():
    print("\n" + "="*60)
    print("  START WEBSITE CONTAINER")
    print("="*60 + "\n")
    
    # Connect via SSH
    log("Connecting to VM via SSH...", "STEP")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        log(f"Connected to {VM_HOST}", "OK")
    except Exception as e:
        log(f"SSH connection failed: {e}", "ERROR")
        return 1
    
    try:
        # Check if there's a running website container and stop it
        log("Stopping any running website containers...", "STEP")
        run_ssh(ssh, "docker stop mycosoft-website 2>/dev/null || true")
        run_ssh(ssh, "docker rm mycosoft-website 2>/dev/null || true")
        run_ssh(ssh, "docker stop mycosoft-always-on-mycosoft-website-1 2>/dev/null || true")
        run_ssh(ssh, "docker rm mycosoft-always-on-mycosoft-website-1 2>/dev/null || true")
        
        # List available website images
        log("Listing available website images...", "STEP")
        output, _, _ = run_ssh(ssh, "docker images | grep -E 'website|mycosoft' | head -10")
        print(f"    Available images:\n{output}")
        
        # Find the correct image (built earlier)
        log("Finding latest website image...", "STEP")
        output, _, _ = run_ssh(ssh, "docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}' | grep mycosoft | head -5")
        print(f"    {output}")
        
        # Try using the mycosoft-always-on-mycosoft-website image
        image_name = "mycosoft-always-on-mycosoft-website:latest"
        
        # Start the container
        log(f"Starting container with image {image_name}...", "STEP")
        docker_run = f"""docker run -d \
            --name mycosoft-website \
            -p 3000:3000 \
            --restart unless-stopped \
            -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
            --health-cmd "curl -f http://localhost:3000/api/health || exit 1" \
            --health-interval 30s \
            --health-timeout 10s \
            --health-retries 3 \
            {image_name}"""
        
        output, error, code = run_ssh(ssh, docker_run)
        if code != 0:
            log(f"Failed with {image_name}, trying alternate...", "WARN")
            # Try the compose-generated image name
            image_name = "mycosoft-always-on_mycosoft-website:latest"
            docker_run = f"""docker run -d \
                --name mycosoft-website \
                -p 3000:3000 \
                --restart unless-stopped \
                -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
                --health-cmd "curl -f http://localhost:3000/api/health || exit 1" \
                --health-interval 30s \
                --health-timeout 10s \
                --health-retries 3 \
                {image_name}"""
            output, error, code = run_ssh(ssh, docker_run)
        
        if code != 0:
            log(f"Container start failed: {error}", "ERROR")
            # List all images to diagnose
            output, _, _ = run_ssh(ssh, "docker images --format '{{.Repository}}:{{.Tag}}'")
            print(f"    All images:\n{output}")
            return 1
        
        log(f"Container started: {output[:12]}", "OK")
        
        # Wait for healthy
        log("Waiting for container to be healthy (30s)...", "STEP")
        time.sleep(30)
        
        # Check container status
        output, _, _ = run_ssh(ssh, "docker ps --filter name=mycosoft-website --format '{{.Status}}'")
        log(f"Container status: {output}", "OK")
        
        # Verify it responds
        output, _, _ = run_ssh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        log(f"HTTP response: {output}", "OK")
        
        # Check logs
        log("Checking container logs...", "STEP")
        output, _, _ = run_ssh(ssh, "docker logs mycosoft-website 2>&1 | tail -10")
        print(f"    Logs:\n{output}")
        
    finally:
        ssh.close()
    
    print("\n" + "="*60)
    print("  CONTAINER STARTED")
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
