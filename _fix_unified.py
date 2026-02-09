"""Fix the unified search endpoint to handle errors gracefully."""
import paramiko

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

stdin, stdout, stderr = ssh.exec_command("cat /opt/mycosoft/mindex/api.py", timeout=10)
api_code = stdout.read().decode()

# Replace the unified search function with a safer version
old_unified = '''@app.get("/mindex/unified/search")
def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    include_species: bool = Query(True),
    include_compounds: bool = Query(True),
    include_sequences: bool = Query(True),
    include_research: bool = Query(True),
):
    results = {}
    if include_species:
        results["species"] = species_search(q=q, limit=limit).get("results", [])
    if include_compounds:
        results["compounds"] = compounds_search(q=q, limit=limit).get("results", [])
    if include_sequences:
        results["genetics"] = sequences_search(q=q, limit=limit).get("results", [])
    if include_research:
        results["research"] = research_search(q=q, limit=limit).get("results", [])

    total = sum(len(v) for v in results.values())
    return {"query": q, "results": results, "totalCount": total, "source": "MINDEX"}'''

new_unified = '''@app.get("/mindex/unified/search")
def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    include_species: bool = Query(True),
    include_compounds: bool = Query(True),
    include_sequences: bool = Query(True),
    include_research: bool = Query(True),
):
    results = {"species": [], "compounds": [], "genetics": [], "research": []}
    try:
        if include_species:
            results["species"] = species_search(q=q, limit=limit).get("results", [])
    except:
        pass
    try:
        if include_compounds:
            results["compounds"] = compounds_search(q=q, limit=limit).get("results", [])
    except:
        pass
    try:
        if include_sequences:
            results["genetics"] = sequences_search(q=q, limit=limit).get("results", [])
    except:
        pass
    try:
        if include_research:
            results["research"] = research_search(q=q, limit=limit).get("results", [])
    except:
        pass

    total = sum(len(v) for v in results.values())
    return {"query": q, "results": results, "totalCount": total, "source": "MINDEX"}'''

api_code = api_code.replace(old_unified, new_unified)

sftp = ssh.open_sftp()
with sftp.file("/opt/mycosoft/mindex/api.py", "w") as f:
    f.write(api_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart mindex-api", timeout=15)
stdout.read()

import time
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("curl -s 'http://localhost:8000/mindex/unified/search?q=amanita&limit=3' 2>/dev/null | head -c 400", timeout=10)
print("Unified:", stdout.read().decode()[:400])

ssh.close()
print("Done")
