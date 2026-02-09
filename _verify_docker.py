import paramiko
import time

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "REDACTED_VM_SSH_PASSWORD"

print(f"Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Verify Docker and finish setup
print("\n=== Verifying Docker ===")
stdin, stdout, stderr = ssh.exec_command("sudo docker --version && sudo docker-compose --version && sudo systemctl status docker --no-pager")
time.sleep(5)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(err)

# Add user to docker group
print("\n=== Adding user to docker group ===")
stdin, stdout, stderr = ssh.exec_command("sudo usermod -aG docker mycosoft")
time.sleep(2)
print("Done")

# Create directories
print("\n=== Creating directories ===")
stdin, stdout, stderr = ssh.exec_command("sudo mkdir -p /opt/mycosoft/ledger /opt/mycosoft/mindex /opt/mycosoft/data && sudo chown -R mycosoft:mycosoft /opt/mycosoft && ls -la /opt/mycosoft/")
time.sleep(2)
print(stdout.read().decode())

ssh.close()
print("Setup verified!")
