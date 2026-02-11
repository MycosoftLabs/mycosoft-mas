"""Check Gemini API configuration on MAS VM."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)

# Check env vars in container
stdin, stdout, stderr = client.exec_command('docker exec myca-orchestrator-new env | grep -i gemini', timeout=30)
env = stdout.read().decode()
print('=== GEMINI ENV ===')
print(env if env else 'No GEMINI env vars found')

# Check if we can reach Gemini from VM
stdin, stdout, stderr = client.exec_command(
    'curl -s -o /dev/null -w "%{http_code}" "https://generativelanguage.googleapis.com/v1beta/models" -H "x-goog-api-key: AIzaSyA1XciZWVlg-P0EI5D3tCQzqHkoW877LoY"',
    timeout=30
)
code = stdout.read().decode().strip()
print(f'\n=== GEMINI API CHECK ===')
print(f'HTTP Status: {code}')

# Test actual generation
print('\n=== TESTING GEMINI GENERATION ===')
stdin, stdout, stderr = client.exec_command(
    '''curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" -H 'Content-Type: application/json' -H 'X-goog-api-key: AIzaSyA1XciZWVlg-P0EI5D3tCQzqHkoW877LoY' -X POST -d '{"contents": [{"parts": [{"text": "Say hello in 10 words"}]}]}' | head -c 500''',
    timeout=60
)
result = stdout.read().decode()
print(result if result else 'No response')

client.close()
