#!/usr/bin/env python3
"""Check services on VM vs local Docker Desktop"""

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")

    # Check running containers
    print("\n=== RUNNING CONTAINERS ON VM ===")
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker ps --format 'table {{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())

    # Check loaded images
    print("\n=== DOCKER IMAGES ON VM ===")
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker images --format 'table {{{{.Repository}}}}\\t{{{{.Tag}}}}\\t{{{{.Size}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())

    # Check website content
    print("\n=== WEBSITE TEST ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:3000 | head -20")
    print(stdout.read().decode())

    # Check MINDEX API
    print("\n=== MINDEX API TEST ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8000/api/mindex/health 2>/dev/null || curl -s http://localhost:8000/health 2>/dev/null || echo 'No health endpoint'")
    print(stdout.read().decode())

    # Check MycoBrain
    print("\n=== MYCOBRAIN TEST ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8003/health 2>/dev/null || echo 'No health endpoint'")
    print(stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    main()
