"""Check VM 191 containers and n8n status."""
import os, paramiko

key_path = os.path.expanduser("~/.ssh/myca_vm191")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
ssh.connect("192.168.0.191", username="mycosoft", pkey=pkey, timeout=15)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

print("=== Containers ===")
print(run("sudo docker ps --format '{{.Names}}  {{.Status}}  {{.Ports}}'"))

print("\n=== n8n health ===")
print(run("curl -s http://localhost:5679/healthz 2>/dev/null || echo 'healthz not available'"))
print("HTTP code:", run("curl -s -o /dev/null -w '%{http_code}' http://localhost:5679/ 2>/dev/null"))

print("\n=== Workspace API health ===")
print(run("curl -s http://localhost:8100/health 2>/dev/null"))

print("\n=== Network connectivity from 191 ===")
print("MAS (188:8001):", run("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.188:8001/health 2>/dev/null || echo DOWN"))
print("MINDEX (189:8000):", run("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.189:8000/health 2>/dev/null || echo DOWN"))
print("Bridge (190:8999):", run("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.190:8999/health 2>/dev/null || echo DOWN"))

ssh.close()
