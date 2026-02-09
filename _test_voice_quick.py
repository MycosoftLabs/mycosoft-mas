"""Quick voice command test"""
import asyncio
from scripts.voice_command_router import route_voice_command

async def test():
    commands = [
        'go to Tokyo',
        'zoom in',
        'show satellites layer',
        'show me a 24 hour forecast',
        'pan left'
    ]
    
    for cmd in commands:
        print(f'\n[TEST] "{cmd}"')
        result = await route_voice_command(cmd)
        print(f'  Domain: {result.get("domain", "?")}')
        print(f'  Action: {result.get("action", "?")}')
        print(f'  Speak: {result.get("speak", "?")}')
        if result.get('frontend_command'):
            print(f'  Frontend: {result["frontend_command"]}')

asyncio.run(test())
