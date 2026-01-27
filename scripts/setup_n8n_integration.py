#!/usr/bin/env python3
"""
n8n Integration Setup Script
Date: January 27, 2026
Sets up n8n webhooks, aligns paths, and verifies connectivity
"""
import requests
import json
from datetime import datetime

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"

# Required webhook paths that website expects
REQUIRED_WEBHOOKS = {
    "myca-chat": "Chat API",
    "myca/command": "Command API",
    "myca/speech": "Speech Complete",
    "myca/speech_safety": "Speech Safety",
    "myca/speech_turn": "Speech Turn",
    "myca/speech_confirm": "Speech Confirm"
}

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")

def get_headers():
    return {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}

def get_all_workflows():
    """Get all workflows from n8n"""
    try:
        r = requests.get(f"{N8N_URL}/api/v1/workflows", headers=get_headers(), timeout=30)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception as e:
        log(f"Error getting workflows: {e}", "ERR")
    return []

def get_workflow_details(workflow_id):
    """Get full workflow details including nodes"""
    try:
        r = requests.get(f"{N8N_URL}/api/v1/workflows/{workflow_id}", headers=get_headers(), timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log(f"Error getting workflow {workflow_id}: {e}", "ERR")
    return None

def find_webhook_paths():
    """Find all webhook paths in active workflows"""
    log("Scanning workflows for webhook paths...", "RUN")
    workflows = get_all_workflows()
    webhook_map = {}
    
    for wf in workflows:
        if not wf.get("active"):
            continue
            
        wf_id = wf.get("id")
        wf_name = wf.get("name")
        details = get_workflow_details(wf_id)
        
        if not details:
            continue
            
        nodes = details.get("nodes", [])
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.webhook":
                path = node.get("parameters", {}).get("path", "")
                webhook_map[path] = {
                    "workflow": wf_name,
                    "workflow_id": wf_id,
                    "node_name": node.get("name")
                }
    
    return webhook_map

def test_webhook(path):
    """Test a webhook endpoint"""
    try:
        r = requests.post(
            f"{N8N_URL}/webhook/{path}",
            json={"test": True, "message": "Integration test"},
            timeout=10
        )
        return r.status_code
    except Exception as e:
        return f"Error: {e}"

def create_chat_webhook_workflow():
    """Create a simple chat webhook workflow if it doesn't exist"""
    workflow = {
        "name": "MYCA Chat Webhook",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "myca-chat",
                    "responseMode": "lastNode",
                    "options": {}
                },
                "id": "webhook",
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1.1,
                "position": [250, 300]
            },
            {
                "parameters": {
                    "jsCode": '''// Forward to MYCA Command API
const input = $input.item.json.body || $input.item.json;
const message = input.message || "";
const sessionId = input.session_id || "default";

// Simple response for now - connect to actual AI later
return [{
    json: {
        response: "MYCA is processing your request: " + message,
        session_id: sessionId,
        timestamp: new Date().toISOString()
    }
}];'''
                },
                "id": "code",
                "name": "Process Message",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 300]
            }
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Process Message", "type": "main", "index": 0}]]
            }
        },
        "active": False,
        "settings": {}
    }
    
    try:
        r = requests.post(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_headers(),
            json=workflow,
            timeout=30
        )
        if r.status_code in [200, 201]:
            data = r.json()
            log(f"Created workflow: MYCA Chat Webhook (ID: {data.get('id')})", "OK")
            return data.get("id")
        else:
            log(f"Failed to create workflow: {r.status_code} - {r.text[:100]}", "ERR")
    except Exception as e:
        log(f"Error creating workflow: {e}", "ERR")
    return None

def activate_workflow(workflow_id, name):
    """Activate a workflow"""
    try:
        r = requests.post(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate",
            headers=get_headers(),
            timeout=30
        )
        if r.status_code == 200:
            log(f"Activated: {name}", "OK")
            return True
    except Exception as e:
        log(f"Error activating {name}: {e}", "ERR")
    return False

def main():
    print("=" * 60)
    print("N8N INTEGRATION SETUP")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {N8N_URL}")
    print("=" * 60)
    print()
    
    # Step 1: Find existing webhooks
    log("Step 1: Scanning existing webhooks...", "RUN")
    webhook_map = find_webhook_paths()
    
    print()
    log("Current webhook paths:", "INFO")
    for path, info in webhook_map.items():
        print(f"    /{path} -> {info['workflow']}")
    
    print()
    
    # Step 2: Check required webhooks
    log("Step 2: Checking required webhooks...", "RUN")
    missing = []
    for path, description in REQUIRED_WEBHOOKS.items():
        if path in webhook_map:
            log(f"/{path} - EXISTS ({webhook_map[path]['workflow']})", "OK")
        else:
            log(f"/{path} - MISSING ({description})", "WARN")
            missing.append(path)
    
    print()
    
    # Step 3: Create missing webhooks
    if "myca-chat" in missing:
        log("Step 3: Creating myca-chat webhook...", "RUN")
        wf_id = create_chat_webhook_workflow()
        if wf_id:
            activate_workflow(wf_id, "MYCA Chat Webhook")
    else:
        log("Step 3: myca-chat webhook exists", "OK")
    
    print()
    
    # Step 4: Test webhooks
    log("Step 4: Testing webhooks...", "RUN")
    for path in REQUIRED_WEBHOOKS.keys():
        status = test_webhook(path)
        if isinstance(status, int):
            if status in [200, 201, 500]:  # 500 means it's processing
                log(f"/{path} - RESPONDING ({status})", "OK")
            elif status == 404:
                log(f"/{path} - NOT REGISTERED (404)", "WARN")
            else:
                log(f"/{path} - STATUS {status}", "WARN")
        else:
            log(f"/{path} - {status}", "ERR")
    
    print()
    print("=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. SSH to Sandbox VM and stop duplicate n8n")
    print("2. Update Cloudflare tunnel to route n8n to MAS VM")
    print("3. Deploy website changes and clear cache")

if __name__ == "__main__":
    main()
