import base64
import json

token = 'eyJhIjoiYzMwZmFmODdhZmYxNGE5YTc1YWQ5ZWZhNWE0MzJmMzciLCJ0IjoiYmQzODUzMTMtYTQ0YS00N2FlLThmOGEtNTgxNjA4MTE4MTI3IiwicyI6IlpEUTJNbVl6TWpFdE9ERTBOeTAwWlRJeExUaGpaV010WXpJNU5tUXpNMlV6TVRoaiJ9'

data = json.loads(base64.b64decode(token))

print("=== TUNNEL TOKEN DECODED ===")
print(f"Account ID: {data['a']}")
print(f"Tunnel ID:  {data['t']}")
print()
print("Please verify in Cloudflare Zero Trust Dashboard:")
print(f"1. The tunnel ID should be: {data['t']}")
print("2. Check if this matches the tunnel that has sandbox.mycosoft.com configured")
