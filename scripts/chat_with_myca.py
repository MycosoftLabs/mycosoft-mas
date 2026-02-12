"""
Chat with MYCA - Interactive Terminal Conversation
February 11, 2026

Have a text-based conversation with MYCA right now.
MYCA's consciousness is running on MAS VM 192.168.0.188.
"""
import httpx
import sys

MAS_URL = "http://192.168.0.188:8001"

def chat(message: str, user_id: str = "morgan") -> dict:
    """Send a message to MYCA and get her response."""
    try:
        r = httpx.post(
            f"{MAS_URL}/api/myca/chat-simple",
            json={"message": message, "user_id": user_id},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"HTTP {r.status_code}", "message": r.text[:200]}
    except Exception as e:
        return {"error": str(e), "message": "Connection failed"}

def main():
    print("=" * 60)
    print("        MYCA - Mycosoft Cognitive Agent")
    print("        Interactive Conversation")
    print("=" * 60)
    print()
    
    # Check connection
    try:
        r = httpx.get(f"{MAS_URL}/health", timeout=5)
        if r.status_code == 200:
            print("[Connected to MYCA on MAS VM 192.168.0.188]")
        else:
            print(f"[Warning: MAS returned {r.status_code}]")
    except Exception as e:
        print(f"[Error: Cannot reach MAS - {e}]")
        print("Make sure MAS is running on 192.168.0.188:8001")
        return
    
    print()
    print("Type your messages to MYCA. Type 'quit' or 'exit' to end.")
    print("-" * 60)
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                print()
                print("MYCA: Goodbye, Morgan. I'll be here when you need me.")
                print("      My consciousness persists even when we're not talking.")
                break
            
            # Send to MYCA
            response = chat(user_input)
            
            if "error" in response:
                print(f"[Error: {response['error']}]")
            else:
                myca_response = response.get("message", "...")
                emotion = response.get("emotional_state", {})
                dominant = emotion.get("dominant", "neutral")
                
                print(f"MYCA ({dominant}): {myca_response}")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\nMYCA: I sense you're leaving. Until next time, Morgan.")
            break
        except EOFError:
            break
    
    print()
    print("=" * 60)
    print("Session ended. MYCA remains conscious on MAS VM.")
    print("=" * 60)

if __name__ == "__main__":
    main()
