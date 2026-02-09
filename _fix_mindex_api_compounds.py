"""Fix MINDEX API compounds/research queries to use correct column names."""
import paramiko

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Read current API, fix the SQL queries
stdin, stdout, stderr = ssh.exec_command("cat /opt/mycosoft/mindex/api.py", timeout=10)
api_code = stdout.read().decode()

# Fix compounds search: formula -> molecular_formula
api_code = api_code.replace(
    "WHERE name ILIKE %s OR formula ILIKE %s",
    "WHERE name ILIKE %s OR molecular_formula ILIKE %s"
)

# Fix compounds result mapping
api_code = api_code.replace(
    '"formula": r.get("formula", ""),',
    '"formula": r.get("molecular_formula", ""),',
)
api_code = api_code.replace(
    '"chemicalClass": r.get("chemical_class", "") or "",',
    '"chemicalClass": r.get("compound_class", "") or "",',
)

# Fix research results mapping to handle jsonb authors
api_code = api_code.replace(
    '"authors": r.get("authors", []) or [],',
    '"authors": r.get("authors") if isinstance(r.get("authors"), list) else [],',
)
api_code = api_code.replace(
    '"abstract": r.get("abstract", "") or "",',
    '"abstract": r.get("abstract") or "",',
)

# Write back
sftp = ssh.open_sftp()
with sftp.file("/opt/mycosoft/mindex/api.py", "w") as f:
    f.write(api_code)
sftp.close()

# Restart the service
stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart mindex-api", timeout=15)
stdout.read()
import time
time.sleep(3)

# Test
stdin, stdout, stderr = ssh.exec_command("curl -s 'http://localhost:8000/mindex/compounds/search?q=psilocybin&limit=2' 2>/dev/null | head -c 300", timeout=10)
print("Compounds test:", stdout.read().decode()[:300])

stdin, stdout, stderr = ssh.exec_command("curl -s 'http://localhost:8000/mindex/research/search?q=mushroom&limit=2' 2>/dev/null | head -c 300", timeout=10)
print("Research test:", stdout.read().decode()[:300])

stdin, stdout, stderr = ssh.exec_command("curl -s 'http://localhost:8000/mindex/stats' 2>/dev/null", timeout=10)
print("Stats:", stdout.read().decode())

ssh.close()
print("Done")
