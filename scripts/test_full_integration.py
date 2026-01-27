#!/usr/bin/env python3
"""Test full MYCA integration - January 27, 2026
Tests the complete flow from website API to n8n
"""
import requests
import json
from datetime import datetime

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "TEST": "[>]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")

print("=" * 70)
print("FULL INTEGRATION TEST - January 27, 2026")
print("=" * 70)

# Test 1: Direct n8n webhook
log("Test 1: Direct n8n webhook /myca/command", "TEST")
try:
    r = requests.post(
        "http://192.168.0.188:5678/webhook/myca/command",
        json={"message": "Hello MYCA, what is your status?", "action": "chat"},
        timeout=15
    )
    log(f"Status: {r.status_code}", "OK" if r.status_code == 200 else "ERR")
    if r.text:
        log(f"Response: {r.text[:200]}", "INFO")
except Exception as e:
    log(f"Error: {e}", "ERR")

print()

# Test 2: sandbox.mycosoft.com /api/mas/chat
log("Test 2: sandbox.mycosoft.com /api/mas/chat", "TEST")
try:
    r = requests.post(
        "https://sandbox.mycosoft.com/api/mas/chat",
        json={"message": "Hello MYCA", "context": {"source": "test"}},
        timeout=30,
        headers={"Content-Type": "application/json"}
    )
    log(f"Status: {r.status_code}", "OK" if r.status_code == 200 else "ERR")
    if r.text:
        try:
            data = r.json()
            log(f"Response type: {type(data)}", "INFO")
            if isinstance(data, dict):
                for k, v in list(data.items())[:3]:
                    log(f"  {k}: {str(v)[:100]}", "INFO")
        except:
            log(f"Response: {r.text[:200]}", "INFO")
except Exception as e:
    log(f"Error: {e}", "ERR")

print()

# Test 3: MAS API health
log("Test 3: MAS API health endpoint", "TEST")
try:
    r = requests.get("http://192.168.0.188:8001/health", timeout=10)
    log(f"Status: {r.status_code}", "OK" if r.status_code == 200 else "ERR")
    if r.status_code == 200:
        data = r.json()
        log(f"Health: {data.get('status', 'unknown')}", "INFO")
except Exception as e:
    log(f"Error: {e}", "ERR")

print()

# Test 4: sandbox.mycosoft.com API health
log("Test 4: sandbox.mycosoft.com health", "TEST")
try:
    r = requests.get("https://sandbox.mycosoft.com/api/health", timeout=15)
    log(f"Status: {r.status_code}", "OK" if r.status_code == 200 else "ERR")
    if r.status_code == 200:
        data = r.json()
        log(f"Website health: {data.get('status')}", "INFO")
        services = data.get('services', [])
        for svc in services:
            log(f"  - {svc.get('name')}: {svc.get('status')}", "INFO")
except Exception as e:
    log(f"Error: {e}", "ERR")

print()
print("=" * 70)
print("INTEGRATION TEST COMPLETE")
print("=" * 70)
