#!/usr/bin/env python3
"""Feed real speech audio to PersonaPlex bridge and capture returned audio."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import wave
from pathlib import Path

import aiohttp
import numpy as np
import sphn

SAMPLE_RATE = 24000
ROOT = Path(__file__).resolve().parents[1]
INPUT_CANDIDATES = [
    ROOT / "_tts_test.wav",
    ROOT / "_tts_test.mp3",
]
OUTPUT_WAV = ROOT / "artifacts" / "personaplex_reply_capture.wav"


def resolve_input_file() -> Path:
    for candidate in INPUT_CANDIDATES:
        if candidate.exists() and candidate.stat().st_size > 1024:
            return candidate
    raise FileNotFoundError(
        "No valid speech fixture found. Expected one of: "
        + ", ".join(str(p) for p in INPUT_CANDIDATES)
    )


def load_input_pcm() -> np.ndarray:
    input_file = resolve_input_file()
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_file),
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    pcm = np.frombuffer(proc.stdout, dtype=np.float32)
    if pcm.size == 0:
        raise RuntimeError("ffmpeg produced empty PCM stream")
    return pcm


def save_wav(path: Path, pcm: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio_i16 = np.clip(pcm, -1.0, 1.0)
    audio_i16 = (audio_i16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())


async def run() -> int:
    input_pcm = load_input_pcm()
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "http://127.0.0.1:8999/session",
            json={"voice": "moshika"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            if r.status != 200:
                print(f"FAIL session HTTP {r.status}: {await r.text()}")
                return 1
            sid = (await r.json())["session_id"]
            print(f"session {sid[:8]}")

        async with session.ws_connect(f"ws://127.0.0.1:8999/ws/{sid}") as ws:
            bridge_ready = False
            handshake = False
            moshi_ready = False

            for _ in range(360):
                try:
                    msg = await ws.receive(timeout=2)
                except TimeoutError:
                    continue
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    if payload.get("type") == "bridge_ready":
                        if payload.get("local_stt_mode"):
                            print("FAIL local_stt_mode=true")
                            return 2
                        bridge_ready = True
                        print("bridge_ready local_stt=false")
                    elif payload.get("type") == "moshi_ready":
                        moshi_ready = True
                        print("moshi_ready")
                    elif payload.get("type") == "error":
                        print(f"FAIL bridge error: {payload.get('message')}")
                        return 3
                elif msg.type == aiohttp.WSMsgType.BINARY and msg.data and msg.data[0] == 0:
                    handshake = True
                    print("moshi handshake 0x00")
                    break

            if not bridge_ready or not handshake:
                print(
                    f"FAIL readiness bridge_ready={bridge_ready} handshake={handshake} moshi_ready={moshi_ready}"
                )
                return 4

            writer = sphn.OpusStreamWriter(SAMPLE_RATE)
            frame_len = int(SAMPLE_RATE * 0.08)
            sent = 0
            for i in range(0, len(input_pcm), frame_len):
                frame = input_pcm[i : i + frame_len]
                if frame.size == 0:
                    continue
                opus = writer.append_pcm(frame.astype(np.float32))
                if opus:
                    await ws.send_bytes(b"\x01" + opus)
                    sent += 1
                await asyncio.sleep(0.02)

            # End speech with silence to encourage response completion.
            silence = np.zeros(SAMPLE_RATE * 2, dtype=np.float32)
            opus_silence = writer.append_pcm(silence)
            if opus_silence:
                await ws.send_bytes(b"\x01" + opus_silence)
                sent += 1
            print(f"sent_opus_packets {sent}")

            reader = sphn.OpusStreamReader(SAMPLE_RATE)
            audio_packets = 0
            pcm_chunks: list[np.ndarray] = []
            idle_ticks_after_audio = 0
            for _ in range(450):
                try:
                    msg = await ws.receive(timeout=2)
                except TimeoutError:
                    if audio_packets > 0:
                        idle_ticks_after_audio += 1
                        if idle_ticks_after_audio >= 8:
                            break
                    continue
                if msg.type == aiohttp.WSMsgType.BINARY and msg.data:
                    if msg.data[0] == 1:
                        audio_packets += 1
                        idle_ticks_after_audio = 0
                        pcm = reader.append_bytes(msg.data[1:])
                        if pcm is not None and len(pcm) > 0:
                            pcm_chunks.append(pcm.astype(np.float32))
                        if audio_packets in (1, 5, 10):
                            print(f"audio_out_packets {audio_packets}")
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    if payload.get("type") == "text":
                        print("myca_text", (payload.get("text") or "")[:80])
                    elif payload.get("type") == "error":
                        print(f"FAIL runtime error: {payload.get('message')}")
                        return 5

            if audio_packets == 0:
                print("FAIL no audio packets returned")
                return 6

            if pcm_chunks:
                all_pcm = np.concatenate(pcm_chunks)
                save_wav(OUTPUT_WAV, all_pcm)
                print(f"captured_wav {OUTPUT_WAV}")
                print(f"captured_seconds {all_pcm.size / SAMPLE_RATE:.2f}")

            print("PASS bridge returned audio")
            return 0


def main() -> None:
    rc = asyncio.run(run())
    sys.exit(rc)


if __name__ == "__main__":
    main()
