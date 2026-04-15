"""SSH 241: test github.com SSH; set origin to SSH; git lfs pull tokenizer."""
import paramiko
from pathlib import Path

k = str(Path.home() / ".ssh" / "id_ed25519")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.241", username="owner1", key_filename=k, timeout=30)
ps = (
    "Set-Location 'C:\\Users\\owner1\\mycosoft-mas'; "
    "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1; "
    "git remote set-url origin git@github.com:MycosoftLabs/mycosoft-mas.git; "
    "git remote -v; "
    "git lfs pull --include='models/personaplex-7b-v1/tokenizer-e351c8d8-checkpoint125.safetensors' 2>&1; "
    "(Get-Item 'models\\personaplex-7b-v1\\tokenizer-e351c8d8-checkpoint125.safetensors').Length"
)
_, o, e = c.exec_command(
    "powershell -NoProfile -ExecutionPolicy Bypass -Command " + repr(ps),
    timeout=2400,
)
print((o.read() + e.read()).decode("utf-8", errors="replace"))
c.close()
