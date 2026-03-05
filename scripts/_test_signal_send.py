#!/usr/bin/env python3
"""Test Signal send via REST API."""
import json
import urllib.request

data = json.dumps({
    "message": "Hello Morgan, MYCA Signal comms are live via REST API. All systems operational.",
    "number": "+18023286922",
    "recipients": ["+16197213384"],
}).encode()

req = urllib.request.Request(
    "http://localhost:8089/v2/send",
    data=data,
    headers={"Content-Type": "application/json"},
)

try:
    resp = urllib.request.urlopen(req)
    print(f"OK: {resp.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(f"Body: {e.read().decode()}")
