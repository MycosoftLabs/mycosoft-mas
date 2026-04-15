"""SSH 241: override LFS fetchinclude (repo has fetchexclude=*), then pull tokenizer blob."""
import paramiko
from pathlib import Path

k = str(Path.home() / ".ssh" / "id_ed25519")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.241", username="owner1", key_filename=k, timeout=30)
ps = (
    "Set-Location 'C:\\Users\\owner1\\mycosoft-mas'; "
    "git config --local lfs.fetchinclude 'models/personaplex-7b-v1/tokenizer-e351c8d8-checkpoint125.safetensors'; "
    "git lfs pull; "
    "git lfs checkout models/personaplex-7b-v1/tokenizer-e351c8d8-checkpoint125.safetensors 2>$null; "
    "Get-Item 'models\\personaplex-7b-v1\\tokenizer-e351c8d8-checkpoint125.safetensors' | Select-Object Length"
)
_, o, e = c.exec_command(
    "powershell -NoProfile -ExecutionPolicy Bypass -Command " + repr(ps),
    timeout=2400,
)
print((o.read() + e.read()).decode("utf-8", errors="replace"))
c.close()
