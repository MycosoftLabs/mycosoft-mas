#!/usr/bin/env python3
"""Check MAS Agent Architecture - Why 16 containers vs 223 agents?"""

import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!')

    # Check actual running containers
    print('=== RUNNING CONTAINERS (Active) ===')
    stdin, stdout, stderr = ssh.exec_command('docker ps --format "{{.Names}}" | sort')
    containers = stdout.read().decode().strip().split('\n')
    for c in containers:
        print(f"  - {c}")
    print(f"\nTotal running: {len(containers)}")

    # Check all containers (including stopped)
    print('\n=== ALL CONTAINERS (including stopped) ===')
    stdin, stdout, stderr = ssh.exec_command('docker ps -a --format "{{.Names}}\t{{.Status}}" | sort')
    all_containers = stdout.read().decode().strip().split('\n')
    print(f"Total defined: {len(all_containers)}")

    # Check orchestrator's agent registry endpoint
    print('\n=== ORCHESTRATOR AGENT REGISTRY (/agents) ===')
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/agents 2>/dev/null')
    output = stdout.read().decode()
    print(output[:3000] if output else "No response from orchestrator")

    # Check orchestrator health
    print('\n=== ORCHESTRATOR HEALTH ===')
    stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8001/health 2>/dev/null')
    print(stdout.read().decode()[:500])

    ssh.close()

if __name__ == "__main__":
    main()
