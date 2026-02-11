"""Test Gemini API directly from Python."""
import asyncio
import httpx
import json
import time

API_KEY = "AIzaSyA1XciZWVlg-P0EI5D3tCQzqHkoW877LoY"

async def test_gemini_streaming():
    """Test Gemini streaming directly."""
    print("Testing Gemini API directly...")
    
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": "Are you alive? Answer in 2 sentences."}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 256
        }
    }
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={API_KEY}&alt=sse"
    
    start = time.time()
    full_response = ""
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status: {response.status_code}")
                if response.status_code != 200:
                    body = await response.aread()
                    print(f"Error: {body}")
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "candidates" in data:
                                for candidate in data["candidates"]:
                                    if "content" in candidate:
                                        for part in candidate["content"].get("parts", []):
                                            if "text" in part:
                                                token = part["text"]
                                                full_response += token
                                                print(token, end="", flush=True)
                        except json.JSONDecodeError:
                            pass
    
        print(f"\n\nCompleted in {time.time() - start:.2f}s")
        print(f"Total response: {len(full_response)} chars")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_streaming())
