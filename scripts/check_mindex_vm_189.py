#!/usr/bin/env python3
"""Quick health check for MINDEX VM 189: Docker containers and services."""
import paramiko

def run(ssh, cmd, timeout=15):
    i, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(), e.read().decode()

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.189", username="mycosoft", password="REDACTED_VM_SSH_PASSWORD", timeout=10)
    print("=== Docker on 189 ===")
    out, err = run(c, "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")
    print(out or err)
    print("=== MINDEX API (8000) ===")
    out2, _ = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/health 2>/dev/null || echo no-api")
    print("  HTTP:", out2.strip() if out2 else "no-api")
    print("=== Qdrant (6333) ===")
    out3, _ = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:6333/ 2>/dev/null")
    print("  HTTP:", out3.strip() if out3 else "n/a")
    c.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
