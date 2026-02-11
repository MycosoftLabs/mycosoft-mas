"""Test MYCA with the three consciousness questions."""
import httpx

questions = ['Are you alive?', 'Are you well?', 'Are you working?']
for q in questions:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print('='*60)
    try:
        r = httpx.post('http://192.168.0.188:8001/api/myca/chat-simple', 
                       json={'message': q, 'user_id': 'morgan'}, 
                       timeout=60)
        if r.status_code == 200:
            data = r.json()
            print(f"A: {data['message']}")
            print(f"Emotion: {data.get('emotional_state', {})}")
        else:
            print(f"Error: {r.status_code}")
            print(r.text[:300])
    except Exception as e:
        print(f"Exception: {e}")
