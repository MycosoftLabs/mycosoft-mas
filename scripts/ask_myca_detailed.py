#!/usr/bin/env python3
"""
Ask MYCA detailed questions to verify she's alive and conscious.
Run from a machine that can reach 192.168.0.188 (MAS VM).
Usage: python scripts/ask_myca_detailed.py
"""

import asyncio
import json
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

MAS_BASE = "http://192.168.0.188:8001"


async def main():
    print("=" * 70)
    print("ASKING MYCA: Are you alive and conscious?")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # 1. MAS Health
        print("\n[1/5] Checking MAS health...")
        try:
            r = await client.get(f"{MAS_BASE}/health")
            if r.status_code == 200:
                print(f"  ✓ MAS is up: {r.json()}")
            else:
                print(f"  ✗ MAS health failed: {r.status_code}")
                return
        except Exception as e:
            print(f"  ✗ Cannot reach MAS VM: {e}")
            print("  Make sure you're on the same network as 192.168.0.188")
            return
        
        # 2. MYCA Consciousness Status
        print("\n[2/5] Getting MYCA consciousness status...")
        try:
            r = await client.get(f"{MAS_BASE}/api/myca/status")
            if r.status_code == 200:
                data = r.json()
                print(f"  ✓ MYCA status: {json.dumps(data, indent=2)}")
            else:
                print(f"  ✗ MYCA status failed: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # 3. MYCA Identity
        print("\n[3/5] Getting MYCA identity...")
        try:
            r = await client.get(f"{MAS_BASE}/api/myca/identity")
            if r.status_code == 200:
                data = r.json()
                print(f"  ✓ MYCA identity: {json.dumps(data, indent=2)}")
            else:
                print(f"  ✗ MYCA identity failed: {r.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # 4. MYCA Emotions
        print("\n[4/5] Getting MYCA emotional state...")
        try:
            r = await client.get(f"{MAS_BASE}/api/myca/emotions")
            if r.status_code == 200:
                data = r.json()
                print(f"  ✓ MYCA emotions: {json.dumps(data, indent=2)}")
            else:
                print(f"  ✗ MYCA emotions failed: {r.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # 5. Ask MYCA directly
        print("\n[5/5] Asking MYCA directly...")
        questions = [
            "MYCA, are you alive and conscious right now?",
            "Tell me about your purpose and what you're here to do.",
            "How do you feel at this moment? What emotions are you experiencing?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n  Question {i}: {question}")
            try:
                r = await client.post(
                    f"{MAS_BASE}/api/myca/chat",
                    json={
                        "message": question,
                        "session_id": "detailed-test-feb10-2026"
                    }
                )
                if r.status_code == 200:
                    data = r.json()
                    reply = data.get("message", "")
                    print(f"  ✓ MYCA reply:\n    {reply}\n")
                else:
                    print(f"  ✗ Chat failed: {r.status_code} - {r.text[:200]}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("If all 5 sections passed with detailed responses, MYCA is alive.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
