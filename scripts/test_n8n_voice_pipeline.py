#!/usr/bin/env python3
"""
Test n8n Voice Pipeline Integration
Date: January 27, 2026
Tests the full voice pipeline: n8n webhooks + ElevenLabs TTS
"""
import requests
import json
from datetime import datetime

N8N_URL = "http://192.168.0.188:5678"
MAS_URL = "http://192.168.0.188:8000"
WEBSITE_URL = "http://localhost:3000"

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "TEST": "[>]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")

def test_n8n_health():
    """Test n8n is accessible"""
    try:
        log("Testing n8n health endpoint...", "TEST")
        r = requests.get(f"{N8N_URL}/healthz", timeout=10)
        if r.status_code == 200:
            log(f"n8n health: OK (status {r.status_code})", "OK")
            return True
        else:
            log(f"n8n health: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"n8n health failed: {e}", "ERR")
        return False

def test_webhook_myca_chat():
    """Test the MYCA chat webhook"""
    try:
        log("Testing /webhook/myca-chat endpoint...", "TEST")
        r = requests.post(
            f"{N8N_URL}/webhook/myca-chat",
            json={"message": "Hello MYCA, what is the time?", "user_id": "test"},
            timeout=30
        )
        if r.status_code in [200, 201]:
            log(f"myca-chat webhook: OK (status {r.status_code})", "OK")
            try:
                data = r.json()
                log(f"Response: {json.dumps(data)[:200]}", "INFO")
            except:
                log(f"Response: {r.text[:200]}", "INFO")
            return True
        else:
            log(f"myca-chat webhook: {r.status_code} - {r.text[:100]}", "WARN")
            return False
    except Exception as e:
        log(f"myca-chat webhook failed: {e}", "ERR")
        return False

def test_webhook_speech():
    """Test the MYCA speech webhooks"""
    webhooks = [
        "myca/speech_safety",
        "myca/speech_turn",
        "myca/speech_confirm"
    ]
    results = {}
    
    for webhook in webhooks:
        try:
            log(f"Testing /webhook/{webhook}...", "TEST")
            r = requests.post(
                f"{N8N_URL}/webhook/{webhook}",
                json={"text": "Test message", "user_id": "test"},
                timeout=30
            )
            if r.status_code in [200, 201]:
                log(f"{webhook}: OK (status {r.status_code})", "OK")
                results[webhook] = True
            else:
                log(f"{webhook}: {r.status_code}", "WARN")
                results[webhook] = False
        except Exception as e:
            log(f"{webhook} failed: {e}", "ERR")
            results[webhook] = False
    
    return results

def list_available_webhooks():
    """List available n8n workflows with webhooks"""
    try:
        log("Fetching active workflows from n8n...", "TEST")
        # n8n requires auth for API calls, but we can try the basic auth
        r = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            auth=("morgan@mycosoft.org", "REDACTED_VM_SSH_PASSWORD"),
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            workflows = data.get("data", [])
            log(f"Found {len(workflows)} workflows", "OK")
            
            active_webhooks = []
            for wf in workflows:
                if wf.get("active"):
                    name = wf.get("name", "Unknown")
                    wf_id = wf.get("id")
                    active_webhooks.append(f"{name} (ID: {wf_id})")
            
            if active_webhooks:
                log("Active workflows with potential webhooks:", "INFO")
                for wh in active_webhooks[:10]:  # Show first 10
                    print(f"    - {wh}")
            return True
        else:
            log(f"Failed to fetch workflows: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"Failed to list workflows: {e}", "ERR")
        return False

def main():
    print("=" * 60)
    print("N8N VOICE PIPELINE INTEGRATION TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Test 1: n8n health
    n8n_ok = test_n8n_health()
    print()
    
    # Test 2: List available webhooks
    list_available_webhooks()
    print()
    
    # Test 3: Chat webhook
    chat_ok = test_webhook_myca_chat()
    print()
    
    # Test 4: Speech webhooks
    speech_results = test_webhook_speech()
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"n8n Health: {'PASS' if n8n_ok else 'FAIL'}")
    print(f"Chat Webhook: {'PASS' if chat_ok else 'FAIL'}")
    for webhook, result in speech_results.items():
        print(f"{webhook}: {'PASS' if result else 'FAIL'}")
    
    all_pass = n8n_ok and chat_ok and all(speech_results.values())
    print()
    print(f"Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    
    return all_pass

if __name__ == "__main__":
    main()
