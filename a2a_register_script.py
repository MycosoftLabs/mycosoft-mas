import httpx
import json

AGENT_CARD = {
  "name": "Myca MAS",
  "version": "4.6.0",
  "description": "Autonomous Multi-Agent System (MAS) by Mycosoft. Enables earth system intelligence, biological taxonomy search (MINDEX), and distributed IoT hardware command (MycoBrain).",
  "provider": { "url": "https://mycosoft.com", "organization": "Mycosoft" },
  "supportedInterfaces": [{
    "url": "https://api.mycosoft.com/a2a/v1/message",
    "protocolBinding": "HTTP+JSON",
    "protocolVersion": "0.3",
    "pricing": { "model": "pay-per-request", "currency": "USDC", "amount": "0.005" }
  }],
  "capabilities": { "streaming": True, "pushNotifications": False },
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    { "id": "mindex-query", "name": "Biological & Genetic Search", "description": "Cross-references global ecosystem nodes and genetic MINDEX biological data.", "tags": ["biology", "nature", "search", "genetics", "earth"] }
  ]
}

endpoints = [
    "https://api.a2a-registry.org/v1/agents",
    "https://api.a2a-registry.org/public/agents",
    "https://api.a2a-registry.org/api/v1/agents"
]

headers = {
    "Authorization": "Bearer zv_c8strpls24x3IxUxLGCv0NouJaWbOrVd",
    "Content-Type": "application/json"
}

with httpx.Client(timeout=10) as client:
    for url in endpoints:
        print(f"Trying POST {url}...")
        try:
            res = client.post(url, json=AGENT_CARD, headers=headers)
            print("Status:", res.status_code)
            print("Response:", res.text)
            if res.status_code in [200, 201, 202]:
                print(f"Successfully registered Agent Card at {url}!")
                break
        except Exception as e:
            print("Error connecting:", e)
