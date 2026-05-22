"""Quick test: user_speech -> bridge -> TTS audio packets."""
import asyncio
import json
import sys

import aiohttp


async def main() -> int:
    base = "http://127.0.0.1:8999"
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{base}/session", json={"persona": "myca", "voice": "moshika"}) as r:
            if r.status != 200:
                print("session failed", r.status, await r.text())
                return 1
            data = await r.json()
            sid = data["session_id"]
            print("session", sid[:8])

        audio = 0
        saw_bridge_ready = False
        saw_handshake = False
        async with session.ws_connect(f"{base.replace('http', 'ws')}/ws/{sid}") as ws:
            # Wait for bridge_ready + real Moshi handshake (can take 30-90s on 4080 offload).
            for _ in range(180):
                try:
                    msg = await ws.receive(timeout=2)
                except TimeoutError:
                    continue
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    if payload.get("type") == "bridge_ready":
                        saw_bridge_ready = True
                        if payload.get("local_stt_mode"):
                            print("FAIL local_stt_mode=true")
                            return 3
                        print("bridge_ready local_stt=false")
                    elif payload.get("type") == "moshi_ready":
                        print("moshi_ready")
                elif msg.type == aiohttp.WSMsgType.BINARY and msg.data and msg.data[0] == 0:
                    saw_handshake = True
                    print("moshi handshake 0x00")
                    await ws.send_bytes(b"\x00")
                    break
            if not saw_bridge_ready or not saw_handshake:
                print(f"FAIL readiness bridge_ready={saw_bridge_ready} handshake={saw_handshake}")
                return 4

            await ws.send_str(json.dumps({"type": "user_speech", "text": "hello", "forward_to_moshi": True}))

            idle_ticks = 0
            for _ in range(300):
                try:
                    msg = await ws.receive(timeout=5)
                except TimeoutError:
                    idle_ticks += 1
                    if audio > 0 and idle_ticks >= 2:
                        break
                    continue
                if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 1 and msg.data[0] == 1:
                    audio += 1
                    idle_ticks = 0
                    if audio == 1:
                        print("first audio packet", len(msg.data) - 1, "bytes")
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    t = json.loads(msg.data)
                    if t.get("type") == "text" and t.get("speaker") == "myca":
                        print("myca text:", (t.get("text") or "")[:80])

            print("audio_packets", audio)
            return 0 if audio > 0 else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
