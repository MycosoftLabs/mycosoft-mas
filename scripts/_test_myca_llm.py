"""Test MYCA LLM via the MAS API — find correct endpoint and test."""
import os, json, urllib.request, urllib.error

mas_url = "http://192.168.0.188:8001"

print(f"Testing MYCA LLM via {mas_url}...")

# Try multiple voice/chat endpoints
endpoints = [
    ("/api/voice/command", "POST", {"message": "Who are you?", "session_id": "test"}),
    ("/voice/command", "POST", {"message": "Who are you?", "session_id": "test"}),
    ("/api/myca/chat", "POST", {"message": "Who are you?", "session_id": "test"}),
    ("/myca/chat", "POST", {"message": "Who are you?", "session_id": "test"}),
    ("/api/chat", "POST", {"message": "Who are you?"}),
    ("/chat", "POST", {"message": "Who are you?"}),
    ("/api/consciousness/chat", "POST", {"message": "Who are you?"}),
]

for path, method, body in endpoints:
    try:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{mas_url}{path}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method=method
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode()
        print(f"SUCCESS {path}: {data[:200]}")
        break
    except urllib.error.HTTPError as e:
        body_resp = e.read().decode()[:80]
        print(f"  {path} -> HTTP {e.code}: {body_resp}")
    except Exception as e:
        print(f"  {path} -> {type(e).__name__}: {str(e)[:60]}")

# List available routes
try:
    r = urllib.request.urlopen(f"{mas_url}/openapi.json", timeout=5)
    api = json.loads(r.read())
    paths = list(api.get("paths", {}).keys())
    voice_paths = [p for p in paths if any(x in p for x in ["voice", "chat", "myca", "llm"])]
    print("\nVoice/chat API routes:")
    for p in voice_paths[:20]:
        print(f"  {p}")
except Exception as e:
    print(f"OpenAPI: {e}")
