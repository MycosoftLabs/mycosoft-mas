#!/usr/bin/env python3
"""
Setup MAS Orchestrator on VM and create systemd service
"""
import paramiko
import time

VM_HOST = '192.168.0.188'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'
MAS_DIR = '/home/mycosoft/mycosoft/mas'

def run_cmd(client, cmd, timeout=60):
    """Run command and return output"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err, exit_code

def run_sudo(client, cmd, timeout=120):
    """Run command with sudo"""
    stdin, stdout, stderr = client.exec_command(f'sudo -S {cmd}', timeout=timeout, get_pty=True)
    stdin.write(VM_PASS + '\n')
    stdin.flush()
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err, exit_code

def main():
    print("Connecting to MAS VM...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print("Connected!")
    
    # Step 1: Install python3.12-venv
    print("\n[1/6] Installing python3.12-venv...")
    out, err, code = run_sudo(client, 'apt-get update -qq')
    print(f"  apt update: exit={code}")
    
    out, err, code = run_sudo(client, 'apt-get install -y python3.12-venv')
    print(f"  apt install: exit={code}")
    if code != 0:
        print(f"  Error: {err[:200]}")
    
    # Step 2: Create venv
    print("\n[2/6] Creating virtual environment...")
    out, err, code = run_cmd(client, f'rm -rf {MAS_DIR}/venv && python3 -m venv {MAS_DIR}/venv')
    print(f"  venv creation: exit={code}")
    if code != 0:
        print(f"  Error: {err}")
    
    # Step 3: Install requirements
    print("\n[3/6] Installing requirements (this may take a few minutes)...")
    out, err, code = run_cmd(client, f'{MAS_DIR}/venv/bin/pip install --upgrade pip', timeout=120)
    print(f"  pip upgrade: exit={code}")
    
    out, err, code = run_cmd(client, f'{MAS_DIR}/venv/bin/pip install -r {MAS_DIR}/requirements.txt', timeout=600)
    print(f"  requirements install: exit={code}")
    if code != 0:
        print(f"  Error (last 300): {err[-300:]}")
    else:
        print("  Requirements installed successfully!")
    
    # Step 4: Create systemd service file
    print("\n[4/6] Creating systemd service...")
    service_content = f'''[Unit]
Description=MYCA MAS Orchestrator
After=network.target

[Service]
Type=simple
User=mycosoft
WorkingDirectory={MAS_DIR}
Environment=PYTHONPATH={MAS_DIR}
ExecStart={MAS_DIR}/venv/bin/python -m mycosoft_mas.core.myca_main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    
    # Write service file
    out, err, code = run_cmd(client, f"echo '{service_content}' > /tmp/mas-orchestrator.service")
    out, err, code = run_sudo(client, 'mv /tmp/mas-orchestrator.service /etc/systemd/system/mas-orchestrator.service')
    print(f"  service file created: exit={code}")
    
    # Step 5: Enable and start service
    print("\n[5/6] Enabling and starting service...")
    out, err, code = run_sudo(client, 'systemctl daemon-reload')
    print(f"  daemon-reload: exit={code}")
    
    out, err, code = run_sudo(client, 'systemctl enable mas-orchestrator')
    print(f"  enable: exit={code}")
    
    out, err, code = run_sudo(client, 'systemctl start mas-orchestrator')
    print(f"  start: exit={code}")
    
    # Step 6: Check status
    print("\n[6/6] Checking service status...")
    time.sleep(3)  # Wait for service to start
    out, err, code = run_sudo(client, 'systemctl status mas-orchestrator --no-pager')
    print(out)
    
    # Verify it's listening
    print("\nChecking if MAS is listening on port 8001...")
    out, err, code = run_cmd(client, 'ss -tlnp | grep 8001')
    if '8001' in out:
        print("SUCCESS: MAS Orchestrator is listening on port 8001!")
    else:
        print("Checking logs for errors...")
        out, err, code = run_sudo(client, 'journalctl -u mas-orchestrator -n 30 --no-pager')
        print(out)
    
    client.close()
    print("\nDone!")

if __name__ == '__main__':
    main()
