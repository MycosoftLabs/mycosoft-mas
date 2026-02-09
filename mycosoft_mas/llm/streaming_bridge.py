"""
Streaming Bridge for PersonaPlex

Handles streaming MYCA brain responses to PersonaPlex for TTS.
Converts text tokens to Moshi-compatible format for injection.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamingChunk:
    """A chunk of streamed response."""
    text: str
    is_final: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PersonaPlexStreamingBridge:
    """
    Bridge between MYCA brain and PersonaPlex TTS.
    
    Handles:
    - Buffering tokens into speakable chunks
    - Converting to Moshi injection format (kind=2)
    - Pacing for natural speech
    """
    
    def __init__(self, min_chunk_size: int = 10, max_chunk_size: int = 100):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.sentence_endings = {".", "!", "?", "\n"}
        self.pause_chars = {",", ";", ":"}
    
    async def stream_to_personaplex(
        self,
        token_stream: AsyncGenerator[str, None],
        send_callback: Callable[[bytes], None]
    ) -> str:
        """
        Stream tokens to PersonaPlex, buffering into speakable chunks.
        
        Args:
            token_stream: Async generator of text tokens
            send_callback: Callback to send bytes to PersonaPlex (kind=2 format)
        
        Returns:
            Full response text
        """
        buffer = ""
        full_response = ""
        
        async for token in token_stream:
            buffer += token
            full_response += token
            
            # Check if we should flush the buffer
            should_flush = False
            
            # Flush on sentence endings
            if any(buffer.rstrip().endswith(p) for p in self.sentence_endings):
                should_flush = True
            
            # Flush on pause characters if buffer is getting long
            elif len(buffer) >= self.min_chunk_size:
                if any(buffer.rstrip().endswith(p) for p in self.pause_chars):
                    should_flush = True
            
            # Force flush if buffer is too long
            if len(buffer) >= self.max_chunk_size:
                should_flush = True
            
            if should_flush:
                chunk = buffer.strip()
                if chunk:
                    # Send as Moshi kind=2 (text injection)
                    message = b"\x02" + chunk.encode("utf-8")
                    try:
                        await send_callback(message)
                        logger.debug(f"[Stream] Sent chunk: {chunk[:30]}...")
                    except Exception as e:
                        logger.error(f"[Stream] Failed to send chunk: {e}")
                    
                    # Small pause for natural pacing
                    await asyncio.sleep(0.05)
                
                buffer = ""
        
        # Flush any remaining buffer
        if buffer.strip():
            message = b"\x02" + buffer.strip().encode("utf-8")
            try:
                await send_callback(message)
            except Exception as e:
                logger.error(f"[Stream] Failed to send final chunk: {e}")
        
        return full_response
    
    def create_injection_message(self, text: str) -> bytes:
        """Create a Moshi-compatible injection message (kind=2)."""
        return b"\x02" + text.encode("utf-8")
    
    async def buffered_stream(
        self,
        token_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[StreamingChunk, None]:
        """
        Buffer tokens into speakable chunks.
        
        Yields:
            StreamingChunk objects ready for TTS
        """
        buffer = ""
        
        async for token in token_stream:
            buffer += token
            
            # Check if we should yield a chunk
            should_yield = False
            
            if any(buffer.rstrip().endswith(p) for p in self.sentence_endings):
                should_yield = True
            elif len(buffer) >= self.min_chunk_size:
                if any(buffer.rstrip().endswith(p) for p in self.pause_chars):
                    should_yield = True
            
            if len(buffer) >= self.max_chunk_size:
                should_yield = True
            
            if should_yield and buffer.strip():
                yield StreamingChunk(text=buffer.strip(), is_final=False)
                buffer = ""
        
        # Final chunk
        if buffer.strip():
            yield StreamingChunk(text=buffer.strip(), is_final=True)


# Singleton instance
_streaming_bridge: Optional[PersonaPlexStreamingBridge] = None


def get_streaming_bridge() -> PersonaPlexStreamingBridge:
    """Get or create the streaming bridge singleton."""
    global _streaming_bridge
    if _streaming_bridge is None:
        _streaming_bridge = PersonaPlexStreamingBridge()
    return _streaming_bridge
