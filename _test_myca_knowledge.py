"""Test MYCA's comprehensive knowledge responses."""

import requests
import json

MAS_URL = "http://192.168.0.188:8001/voice/orchestrator/chat"

test_questions = [
    "What is your name?",
    "Tell me about Mycosoft and what we are building",
    "What science and research do we do?",
    "How many agents do you coordinate?",
    "Tell me about PersonaPlex and voice",
    "What are our plans for the future?",
    "Tell me about our devices like Mushroom1 and Petraeus",
    "What integrations do you have?",
    "Who created you?",
]

print("=" * 70)
print("MYCA Knowledge Test - Comprehensive Responses")
print("=" * 70)

for i, question in enumerate(test_questions, 1):
    print(f"\n--- Question {i}: {question}")
    print("-" * 60)
    
    try:
        response = requests.post(
            MAS_URL,
            json={"message": question},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.ok:
            data = response.json()
            answer = data.get("response_text", "No response")
            print(f"MYCA: {answer}")
        else:
            print(f"Error: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"Exception: {e}")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)
