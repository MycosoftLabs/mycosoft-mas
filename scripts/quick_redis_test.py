"""Quick Redis Pub/Sub Test - February 12, 2026"""

import asyncio
import redis.asyncio as redis

async def main():
    print("Testing Redis pub/sub at 192.168.0.189:6379...")
    
    # Connect
    r = redis.from_url("redis://192.168.0.189:6379/0")
    
    # Test ping
    pong = await r.ping()
    print(f"[OK] Ping: {pong}")
    
    # Test publish
    result = await r.publish("test:channel", "hello")
    print(f"[OK] Published to test:channel, subscribers: {result}")
    
    # Test publish to our channels
    channels = [
        "devices:telemetry",
        "agents:status",
        "experiments:data",
        "crep:live",
    ]
    
    for channel in channels:
        result = await r.publish(channel, '{"test": true}')
        print(f"[OK] Published to {channel}")
    
    await r.close()
    print("\n[SUCCESS] All Redis pub/sub operations successful!")

if __name__ == "__main__":
    asyncio.run(main())
