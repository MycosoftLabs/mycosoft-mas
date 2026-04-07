"""
TTS Fallback for PersonaPlex Bridge - March 2, 2026

Moshi does not support kind 0x02 (text injection) for TTS. This module provides
edge-tts synthesis and Opus encoding so MYCA Voice can produce spoken output.

Flow: text -> edge-tts (MP3) -> ffmpeg (PCM 24kHz mono) -> opuslib -> Opus packets.
Frontend expects 0x01 + raw Opus packets (24kHz, mono, 20ms frames).
"""
import asyncio
import logging
import os
import shutil
from typing import List

logger = logging.getLogger("personaplex-bridge")

# Default voice for MYCA (en-US female, natural)
DEFAULT_VOICE = "en-US-AriaNeural"
SAMPLE_RATE = 24000
CHANNELS = 1
FRAME_SAMPLES = 480  # 20ms at 24kHz
BYTES_PER_FRAME = FRAME_SAMPLES * 2  # s16le


async def synthesize_to_opus(text: str, voice: str = DEFAULT_VOICE) -> List[bytes]:
    """
    Synthesize text to speech and return raw Opus packets (24kHz mono).
    Returns empty list on failure.
    """
    if not text or not text.strip():
        return []

    # ffmpeg: PATH or explicit (Windows installs often omit PATH for the bridge process)
    ffmpeg_path = os.environ.get("FFMPEG_PATH", "").strip() or shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.warning(
            "TTS fallback: ffmpeg not found (set FFMPEG_PATH or add ffmpeg to PATH); edge-tts needs ffmpeg for MP3->PCM"
        )
        return []

    try:
        import edge_tts
    except ImportError:
        logger.warning("TTS fallback: edge-tts not installed; pip install edge-tts")
        return []

    try:
        import opuslib
    except ImportError:
        logger.warning("TTS fallback: opuslib not installed; pip install opuslib")
        return []

    try:
        # 1. edge-tts -> MP3 bytes
        communicate = edge_tts.Communicate(text.strip(), voice)
        mp3_chunks = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                mp3_chunks.append(chunk["data"])
        mp3_bytes = b"".join(mp3_chunks) if mp3_chunks else b""
        if not mp3_bytes:
            logger.warning("TTS fallback: edge-tts produced no audio")
            return []

        # 2. ffmpeg: MP3 -> PCM s16le 24kHz mono
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_path,
            "-y", "-loglevel", "error",
            "-i", "pipe:0",
            "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=mp3_bytes)
        if proc.returncode != 0 or not stdout:
            err = stderr.decode("utf-8", errors="ignore") if stderr else "unknown"
            logger.warning(f"TTS fallback: ffmpeg failed: {err[:200]}")
            return []

        # 3. opuslib: PCM -> Opus packets (20ms frames)
        enc = opuslib.Encoder(SAMPLE_RATE, CHANNELS)
        packets: List[bytes] = []
        for i in range(0, len(stdout), BYTES_PER_FRAME):
            chunk = stdout[i : i + BYTES_PER_FRAME]
            if len(chunk) < BYTES_PER_FRAME:
                break
            pkt = enc.encode(chunk, FRAME_SAMPLES)
            if pkt:
                packets.append(pkt)

        return packets
    except Exception as e:
        logger.error(f"TTS fallback error: {e}", exc_info=True)
        return []
