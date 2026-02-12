"""Simple test to verify voice-memory bridge works."""

import asyncio
import sys

async def test_import():
    """Test importing the bridge."""
    print("Testing import...", flush=True)
    try:
        from mycosoft_mas.voice.memory_bridge import get_voice_memory_bridge
        print("✓ Import successful", flush=True)
        
        # Try initializing
        print("Initializing bridge...", flush=True)
        bridge = await get_voice_memory_bridge()
        print(f"✓ Bridge initialized: {bridge._initialized}", flush=True)
        
        # Get stats
        print("Getting stats...", flush=True)
        stats = await bridge.get_stats()
        print(f"✓ Stats retrieved: {stats}", flush=True)
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting test...", flush=True)
    result = asyncio.run(test_import())
    print(f"Test {'PASSED' if result else 'FAILED'}", flush=True)
    sys.exit(0 if result else 1)
