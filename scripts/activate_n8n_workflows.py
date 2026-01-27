#!/usr/bin/env python3
"""
Activate all MYCA workflows in n8n
Date: January 27, 2026
Uses the n8n API to activate workflows for production webhooks
"""
import requests
from datetime import datetime
import json

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")

def get_workflows():
    """Get all workflows from n8n"""
    try:
        r = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30
        )
        if r.status_code == 200:
            return r.json().get("data", [])
        else:
            log(f"Failed to get workflows: {r.status_code} - {r.text[:100]}", "ERR")
            return []
    except Exception as e:
        log(f"Error getting workflows: {e}", "ERR")
        return []

def activate_workflow(workflow_id, workflow_name):
    """Activate a specific workflow using POST /activate endpoint"""
    try:
        r = requests.post(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30
        )
        if r.status_code in [200, 201]:
            log(f"Activated: {workflow_name}", "OK")
            return True
        else:
            log(f"Failed to activate {workflow_name}: {r.status_code} - {r.text[:100]}", "WARN")
            return False
    except Exception as e:
        log(f"Error activating {workflow_name}: {e}", "ERR")
        return False

def main():
    print("=" * 60)
    print("N8N WORKFLOW ACTIVATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Get all workflows
    log("Fetching all workflows...", "RUN")
    workflows = get_workflows()
    
    if not workflows:
        log("No workflows found or unable to access n8n API", "ERR")
        log("The n8n API might require an API key instead of basic auth", "INFO")
        return
    
    log(f"Found {len(workflows)} workflows", "OK")
    print()
    
    # Filter and activate key MYCA workflows
    key_workflows = [
        "MYCA",
        "Command",
        "Event",
        "Speech",
        "Orchestrator",
        "Master",
        "Jarvis",
        "Router"
    ]
    
    activated = 0
    skipped = 0
    failed = 0
    
    for wf in workflows:
        wf_id = wf.get("id")
        wf_name = wf.get("name", "Unknown")
        is_active = wf.get("active", False)
        
        # Check if this is a key workflow
        is_key = any(key.lower() in wf_name.lower() for key in key_workflows)
        
        if not is_key:
            continue
            
        if is_active:
            log(f"Already active: {wf_name}", "INFO")
            skipped += 1
        else:
            if activate_workflow(wf_id, wf_name):
                activated += 1
            else:
                failed += 1
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Activated: {activated}")
    print(f"Already Active: {skipped}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()
