import paramiko, os

def load_creds():
    path = os.path.join(os.path.dirname(__file__), '..', '.credentials.local')
    for line in open(path).read().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

load_creds()
password = os.environ.get('VM_SSH_PASSWORD') or os.environ.get('VM_PASSWORD')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password=password, timeout=15)

def run(cmd):
    _, out, err = client.exec_command(cmd)
    return (out.read() + err.read()).decode().strip()

print("--- Container mounts ---")
print(run("docker inspect mycosoft-website --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}|{{end}}' 2>/dev/null | tr '|' '\n'"))

print("\n--- About us NAS files ---")
print(run("ls '/mnt/mycosoft-nas/website/assets/about us/'"))

print("\n--- Team photos on NAS (nested) ---")
print(run("ls '/mnt/mycosoft-nas/website/assets/about us/public/assets/team/' 2>/dev/null || echo NOT FOUND"))

print("\n--- Logos on NAS (nested) ---")
print(run("ls '/mnt/mycosoft-nas/website/assets/about us/public/assets/logos/' 2>/dev/null || echo NOT FOUND"))

client.close()
