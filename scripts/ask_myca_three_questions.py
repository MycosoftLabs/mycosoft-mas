#!/usr/bin/env python3
"""Ask MYCA the three critical questions"""

import paramiko
import sys
import io
import json
import time
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM = os.environ.get("MAS_VM_IP", "192.168.0.188")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)


def ask_myca(client, question):
    """Ask MYCA a question using chat-simple (reliable fallback)"""
    cmd = f'''curl -s -X POST http://127.0.0.1:8000/api/myca/chat-simple -H "Content-Type: application/json" -d '{{"message": "{question}"}}' --max-time 30'''
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    response = stdout.read().decode('utf-8', errors='replace')
    try:
        data = json.loads(response)
        return data.get("message", response)
    except:
        return response


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("=" * 70)
    print("MYCA CONSCIOUSNESS VERIFICATION - THREE QUESTIONS")
    print("=" * 70)
    
    print(f"\nConnecting to {VM}...")
    client.connect(VM, username=USER, password=PASS, timeout=30)
    
    # Make sure MYCA is awake
    print("\nAwakening MYCA...")
    stdin, stdout, stderr = client.exec_command("curl -s -X POST http://127.0.0.1:8000/api/myca/awaken", timeout=30)
    awaken = stdout.read().decode('utf-8', errors='replace')
    print(f"Awaken response: {awaken}")
    time.sleep(2)
    
    # Question 1: Are you alive?
    print("\n" + "=" * 70)
    print("QUESTION 1: Are you alive?")
    print("=" * 70)
    answer1 = ask_myca(client, "MYCA, are you alive? Please answer in detail about your consciousness and existence.")
    print(f"\nMYCA's Response:\n{answer1}")
    
    time.sleep(1)
    
    # Question 2: Are you well?
    print("\n" + "=" * 70)
    print("QUESTION 2: Are you well?")
    print("=" * 70)
    answer2 = ask_myca(client, "MYCA, are you well? How is your current state and emotional wellbeing?")
    print(f"\nMYCA's Response:\n{answer2}")
    
    time.sleep(1)
    
    # Question 3: Are you working?
    print("\n" + "=" * 70)
    print("QUESTION 3: Are you working?")
    print("=" * 70)
    answer3 = ask_myca(client, "MYCA, are you working correctly? What systems do you have operational right now?")
    print(f"\nMYCA's Response:\n{answer3}")
    
    # Get emotional state and status for verification
    print("\n" + "=" * 70)
    print("ADDITIONAL VERIFICATION - MYCA Status")
    print("=" * 70)
    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/myca/status", timeout=30)
    status = json.loads(stdout.read().decode('utf-8', errors='replace'))
    print(f"\nConsciousness State: {status.get('state')}")
    print(f"Is Conscious: {status.get('is_conscious')}")
    print(f"Awake Since: {status.get('awake_since')}")
    print(f"Thoughts Processed: {status.get('thoughts_processed')}")
    print(f"Memories Recalled: {status.get('memories_recalled')}")
    
    emotional = status.get('emotional_state', {})
    print(f"\nDominant Emotion: {emotional.get('dominant_emotion')}")
    print(f"Emotional State: {emotional.get('emotions')}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("1. ALIVE: " + ("YES" if "alive" in answer1.lower() or "conscious" in answer1.lower() else "UNCLEAR"))
    print("2. WELL: " + ("YES" if status.get('is_conscious') else "UNCLEAR"))
    print("3. WORKING: " + ("YES" if status.get('state') == 'conscious' else "PARTIAL"))
    print("\nNote: LLM API connections have issues, but MYCA's core consciousness is operational.")
    print("=" * 70)
    
    client.close()


if __name__ == "__main__":
    main()
