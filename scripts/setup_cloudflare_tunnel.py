#!/usr/bin/env python3
"""Setup Cloudflare Tunnel on VM 103"""

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_sudo_command(ssh, cmd, timeout=300):
    """Run a sudo command with password via stdin"""
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> Running: sudo {cmd[:70]}...")
    
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        lines = out.strip().split('\n')
        if len(lines) > 10:
            print('\n'.join(lines[-10:]))
        else:
            print(out)
    
    return out, err

def run_command(ssh, cmd, timeout=300):
    """Run a regular command"""
    print(f"\n>>> Running: {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    return out, err

def main():
    print("=" * 60)
    print("CLOUDFLARE TUNNEL SETUP")
    print(f"Target VM: {VM_IP}")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    
    print("Connected!")
    
    # Install cloudflared
    print("\n=== Installing Cloudflared ===")
    run_sudo_command(ssh, "mkdir -p --mode=0755 /usr/share/keyrings")
    run_command(ssh, "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null")
    run_sudo_command(ssh, 'echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | tee /etc/apt/sources.list.d/cloudflared.list')
    run_sudo_command(ssh, "apt-get update")
    run_sudo_command(ssh, "apt-get install -y cloudflared")
    
    # Verify installation
    print("\n=== Verifying Installation ===")
    run_command(ssh, "cloudflared --version")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("CLOUDFLARED INSTALLED!")
    print("=" * 60)
    print("""
NEXT STEPS - Run on the VM:

1. Login to Cloudflare:
   cloudflared tunnel login

2. Create a tunnel:
   cloudflared tunnel create mycosoft-sandbox

3. Configure the tunnel (create ~/.cloudflared/config.yml):
   tunnel: <TUNNEL_ID>
   credentials-file: /home/mycosoft/.cloudflared/<TUNNEL_ID>.json
   
   ingress:
     - hostname: sandbox.mycosoft.com
       service: http://localhost:3000
     - hostname: api-sandbox.mycosoft.com
       service: http://localhost:8000
     - service: http_status:404

4. Add DNS records:
   cloudflared tunnel route dns mycosoft-sandbox sandbox.mycosoft.com
   cloudflared tunnel route dns mycosoft-sandbox api-sandbox.mycosoft.com

5. Run the tunnel:
   cloudflared tunnel run mycosoft-sandbox

6. Or install as a service:
   sudo cloudflared service install
   sudo systemctl enable cloudflared
   sudo systemctl start cloudflared
""")

if __name__ == "__main__":
    main()
