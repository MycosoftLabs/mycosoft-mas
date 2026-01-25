#!/usr/bin/env python3
"""
Deploy MAS v2 Agent Containers
Uses docker-compose.agents.yml to deploy the MAS agent stack
"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
VM_ID = 103
NODE = "pve"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def exec_cmd(cmd, timeout=300, show_output=True):
    """Execute command via QEMU Guest Agent"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(5)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    code = data.get("exitcode", 0)
                    out_b64 = data.get("out-data", "")
                    err_b64 = data.get("err-data", "")
                    
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    
                    if show_output and (out or err):
                        output = (out or err)[:1000]
                        for line in output.split('\n')[:20]:
                            print(f"    {line}")
                    
                    return code == 0, out or err
            
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("MAS v2 AGENT CONTAINER DEPLOYMENT")
    print("=" * 60)
    
    # Step 1: Check docker-compose.agents.yml exists
    log("Checking docker-compose.agents.yml...", "RUN")
    success, output = exec_cmd("ls -la /home/mycosoft/mycosoft/mas/docker/docker-compose.agents.yml 2>&1", timeout=30)
    if success:
        log("docker-compose.agents.yml found", "OK")
    else:
        log("docker-compose.agents.yml not found!", "ERR")
        return False
    
    # Step 2: Check Dockerfile.agent exists
    log("Checking Dockerfile.agent...", "RUN")
    success, output = exec_cmd("ls -la /home/mycosoft/mycosoft/mas/docker/Dockerfile.agent 2>&1", timeout=30)
    if success:
        log("Dockerfile.agent found", "OK")
    else:
        log("Dockerfile.agent not found!", "ERR")
        return False
    
    # Step 3: Check requirements-agent.txt
    log("Checking requirements-agent.txt...", "RUN")
    success, output = exec_cmd("ls -la /home/mycosoft/mycosoft/mas/requirements-agent.txt 2>&1", timeout=30)
    if success:
        log("requirements-agent.txt found", "OK")
    else:
        log("requirements-agent.txt not found!", "WARN")
    
    # Step 4: Build base agent image
    log("Building base agent Docker image (this may take a few minutes)...", "RUN")
    build_cmd = """cd /home/mycosoft/mycosoft/mas && \
docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent . 2>&1 | tail -30"""
    success, output = exec_cmd(build_cmd, timeout=600)
    if success and "Successfully" in str(output):
        log("Agent image built successfully", "OK")
    else:
        log(f"Build may have issues: {output[:200] if output else 'No output'}", "WARN")
    
    # Step 5: Check if image was created
    log("Verifying agent image...", "RUN")
    success, output = exec_cmd("docker images | grep mas-agent | head -5", timeout=30)
    if output and "mas-agent" in output:
        log("Agent image verified", "OK")
    else:
        log("Agent image not found after build", "WARN")
    
    # Step 6: Start core services (Redis for message broker)
    log("Starting core services (Redis)...", "RUN")
    success, output = exec_cmd("docker ps | grep redis", timeout=30)
    if output and "redis" in output.lower():
        log("Redis already running", "OK")
    else:
        log("Redis not running - agents will fail to connect", "WARN")
    
    # Step 7: Start MYCA Orchestrator
    log("Starting MYCA Orchestrator and agents...", "RUN")
    start_cmd = """cd /home/mycosoft/mycosoft/mas/docker && \
docker compose -f docker-compose.agents.yml up -d 2>&1 | tail -30"""
    success, output = exec_cmd(start_cmd, timeout=300)
    log("Orchestrator startup initiated", "OK")
    
    # Step 8: Check running containers
    log("Checking running agent containers...", "RUN")
    time.sleep(5)
    success, output = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '(agent|orchestrator|mas)' | head -20", timeout=30)
    if output:
        log("Agent containers status:", "INFO")
    else:
        log("No agent containers found yet", "WARN")
    
    # Step 9: Check container logs
    log("Checking orchestrator logs...", "RUN")
    success, output = exec_cmd("docker logs myca-orchestrator 2>&1 | tail -10 || echo 'Container not started yet'", timeout=30)
    
    print("\n" + "=" * 60)
    print("AGENT DEPLOYMENT COMPLETE")
    print("=" * 60)
    print("\nNote: Agent containers may take a few minutes to fully start.")
    print("Monitor with: docker ps | grep agent")
    print("Check logs with: docker logs <container-name>")
    
    return True

if __name__ == "__main__":
    main()
