"""Import all n8n workflow JSONs directly to VM 191's n8n (no tunnel needed)."""
import json, os, glob, sys, base64
import urllib.request, urllib.error

N8N_URL = "http://192.168.0.191:5679"
N8N_USER = "myca"
N8N_PASS = "myca_n8n_2026"

auth = base64.b64encode(f"{N8N_USER}:{N8N_PASS}".encode()).decode()

def n8n_post(path, data):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{N8N_URL}{path}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return {"error": e.code, "body": body}
    except Exception as e:
        return {"error": str(e)}

# Test connection
print(f"Connecting to n8n at {N8N_URL}...")
try:
    req = urllib.request.Request(
        f"{N8N_URL}/healthz",
        headers={"Authorization": f"Basic {auth}"}
    )
    r = urllib.request.urlopen(req, timeout=5)
    print(f"n8n healthy: {r.read().decode()}")
except Exception as e:
    print(f"n8n connection failed: {e}")
    sys.exit(1)

# Collect all workflow files
wf_dirs = [
    os.path.join(os.path.dirname(__file__), "../n8n/workflows"),
    os.path.join(os.path.dirname(__file__), "../workflows/n8n"),
]

wf_files = []
for d in wf_dirs:
    if os.path.isdir(d):
        wf_files.extend(glob.glob(os.path.join(d, "*.json")))

print(f"\nFound {len(wf_files)} workflow files")

imported = 0
failed = 0
skipped = 0

for wf_file in sorted(wf_files):
    name = os.path.basename(wf_file)
    try:
        with open(wf_file, "r", encoding="utf-8") as f:
            wf_data = json.load(f)
    except Exception as e:
        print(f"  SKIP {name}: bad JSON ({e})")
        skipped += 1
        continue

    # n8n import expects the workflow object
    # Handle both formats: direct workflow or wrapped in array
    if isinstance(wf_data, list):
        wf_data = wf_data[0] if wf_data else {}
    
    # Ensure it has a name
    if not wf_data.get("name"):
        wf_data["name"] = name.replace(".json", "").replace("-", " ").title()

    # Remove id so n8n creates a new one
    wf_data.pop("id", None)

    result = n8n_post("/api/v1/workflows", wf_data)
    
    if "error" in result:
        err_code = result.get("error", "?")
        body = result.get("body", "")
        if "duplicate" in body.lower() or err_code == 409:
            skipped += 1
        else:
            print(f"  FAIL {name}: {err_code} {body[:80]}")
            failed += 1
    else:
        wf_id = result.get("id", "?")
        wf_name = result.get("name", name)
        imported += 1

print(f"\nResults: {imported} imported, {skipped} skipped (dupe/bad), {failed} failed")
print(f"Total: {imported + skipped + failed}/{len(wf_files)}")
