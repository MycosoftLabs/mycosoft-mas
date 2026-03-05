"""Runner that captures and prints provision output safely."""
import os, subprocess, sys

env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
result = subprocess.run(
    ["python", r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\_provision_vm191.py"],
    capture_output=True,
    env=env
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")
# Strip unicode box chars for Windows console
for ch in "╔╗╚╝║═":
    out = out.replace(ch, "+")
    err = err.replace(ch, "+")
print(out)
if err and result.returncode != 0:
    print("STDERR:", err[:600])
sys.exit(result.returncode)
