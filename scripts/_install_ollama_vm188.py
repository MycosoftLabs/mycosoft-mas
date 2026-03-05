"""Install Ollama on MAS VM 188 and pull a model."""
import os
import sys
import time
import paramiko

host = "192.168.0.188"
user = "mycosoft"

# Load password from credentials
creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
password = ""
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                password = v.strip()
                break

if not password:
    password = os.environ.get("VM_PASSWORD", "")

print(f"Connecting to {host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=20)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

# Check if ollama is already installed
out, _ = run("which ollama 2>/dev/null || echo NOT_FOUND")
if "NOT_FOUND" in out or not out.strip():
    print("Ollama not installed. Installing...")
    # Write install script
    sftp = ssh.open_sftp()
    install_script = (
        "#!/bin/bash\n"
        "set -e\n"
        "curl -fsSL https://ollama.com/install.sh | sh\n"
        "echo INSTALL_DONE\n"
    )
    with sftp.open("/tmp/install_ollama.sh", "w") as f:
        f.write(install_script)
    sftp.chmod("/tmp/install_ollama.sh", 0o755)
    sftp.close()

    # Run with sudo
    transport = ssh.get_transport()
    chan = transport.open_session()
    chan.get_pty()
    chan.exec_command(f"echo {password} | sudo -S bash /tmp/install_ollama.sh")
    
    print("Installing Ollama (this takes ~60s)...")
    time.sleep(90)
    out_bytes = b""
    while chan.recv_ready():
        out_bytes += chan.recv(8192)
    install_out = out_bytes.decode("utf-8", errors="replace")
    print("Install output:", install_out[-500:])
    
    if "INSTALL_DONE" in install_out or "installed" in install_out.lower():
        print("Ollama installed successfully.")
    else:
        print("Install may have failed - check output above.")
else:
    print(f"Ollama already installed at: {out.strip()}")

# Start Ollama service
print("Starting Ollama service...")
out, err = run(f"echo {password} | sudo -S systemctl start ollama 2>&1 || ollama serve &>/tmp/ollama.log &")
print("Start:", out[:100], err[:100])
time.sleep(5)

# Check if running
out, _ = run("curl -s http://localhost:11434/api/tags 2>/dev/null || echo OFFLINE")
print("Ollama status:", out[:200])

if "OFFLINE" not in out and out.strip():
    print("Ollama is running!")
    # Check if model is available
    import json
    try:
        tags = json.loads(out)
        models = [m["name"] for m in tags.get("models", [])]
        print(f"Available models: {models}")
        
        if not any("llama" in m for m in models):
            print("Pulling llama3.2:3b (small, fast model)...")
            # Pull in background
            transport = ssh.get_transport()
            chan = transport.open_session()
            chan.exec_command("ollama pull llama3.2:3b &>/tmp/ollama_pull.log &")
            time.sleep(5)
            out, _ = run("cat /tmp/ollama_pull.log 2>/dev/null | tail -5")
            print("Pull started:", out[:200])
        else:
            print(f"Model already available: {models}")
    except Exception as e:
        print(f"Could not parse tags: {e}")
else:
    print("Ollama still offline after start attempt. Check manually on VM 188.")

ssh.close()
print("Done.")
