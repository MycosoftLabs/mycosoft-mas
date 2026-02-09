#!/usr/bin/env python3
"""Test Moshi WebSocket fix for None text_prompt_tokens"""
import asyncio
import aiohttp
import time

async def test_ws(url, name):
    print(f'\nTest: {name}')
    print(f'URL: {url[:80]}...' if len(url) > 80 else f'URL: {url}')
    try:
        start = time.time()
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(url, timeout=aiohttp.ClientTimeout(total=15)) as ws:
                print(f'Connected in {time.time()-start:.2f}s')
                msg = await asyncio.wait_for(ws.receive(), timeout=10)
                if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b'\x00':
                    print(f'HANDSHAKE OK in {time.time()-start:.2f}s')
                    return True
                else:
                    print(f'Unexpected: {msg.type}')
    except asyncio.TimeoutError:
        print(f'TIMEOUT after {time.time()-start:.2f}s')
    except Exception as e:
        print(f'Error: {e}')
    return False

async def main():
    print("=" * 60)
    print("MOSHI WEBSOCKET FIX TEST")
    print("=" * 60)
    
    # Test without text_prompt (was failing before the fix)
    r1 = await test_ws('ws://localhost:8998/api/chat', 'No text_prompt (was crashing)')
    
    # Test with text_prompt
    r2 = await test_ws('ws://localhost:8998/api/chat?text_prompt=You%20are%20MYCA', 'With text_prompt')
    
    print(f'\n{"=" * 60}')
    print('RESULTS')
    print("=" * 60)
    status1 = "PASS" if r1 else "FAIL"
    status2 = "PASS" if r2 else "FAIL"
    print(f'No prompt:   [{status1}]')
    print(f'With prompt: [{status2}]')
    
    if r1 and r2:
        print('\n[OK] Fix verified! Both cases work.')
    else:
        print('\n[ERROR] Some tests failed.')

if __name__ == "__main__":
    asyncio.run(main())
