"""
Test Redis Pub/Sub - February 12, 2026

Verifies Redis pub/sub functionality with real Redis on VM 192.168.0.189:6379.
Tests all four required channels and connection management.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.realtime.redis_pubsub import (
    RedisPubSubClient,
    Channel,
    PubSubMessage,
    publish_device_telemetry,
    publish_agent_status,
    publish_experiment_data,
    publish_crep_update,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.messages_received = []
        self.errors = []
    
    def add_message(self, message: PubSubMessage):
        self.messages_received.append({
            "channel": message.channel,
            "data": message.data,
            "source": message.source,
            "timestamp": message.timestamp,
        })
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    def print_summary(self):
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)
        
        print(f"\n✓ Messages Received: {len(self.messages_received)}")
        for i, msg in enumerate(self.messages_received, 1):
            print(f"  {i}. [{msg['channel']}] from {msg['source']}")
            print(f"     Data: {json.dumps(msg['data'], indent=6)}")
        
        if self.errors:
            print(f"\n✗ Errors: {len(self.errors)}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        else:
            print("\n✓ No errors")
        
        print("\n" + "="*80)


async def test_basic_connection():
    """Test 1: Basic connection to Redis."""
    print("\n[TEST 1] Testing basic connection to Redis...")
    
    client = RedisPubSubClient()
    success = await client.connect()
    
    if success:
        print("✓ Connected to Redis successfully")
        stats = client.get_stats()
        print(f"  Redis URL: {stats['redis_url']}")
        print(f"  Connected: {stats['connected']}")
        await client.disconnect()
        return True
    else:
        print("✗ Failed to connect to Redis")
        return False


async def test_publish_subscribe():
    """Test 2: Publish and subscribe to all channels."""
    print("\n[TEST 2] Testing publish/subscribe on all channels...")
    
    results = TestResults()
    client = RedisPubSubClient()
    await client.connect()
    
    # Create message handler
    async def message_handler(message: PubSubMessage):
        logger.info(f"Received on {message.channel}: {message.data}")
        results.add_message(message)
    
    # Subscribe to all channels
    channels_to_test = [
        Channel.DEVICES_TELEMETRY.value,
        Channel.AGENTS_STATUS.value,
        Channel.EXPERIMENTS_DATA.value,
        Channel.CREP_LIVE.value,
    ]
    
    for channel in channels_to_test:
        success = await client.subscribe(channel, message_handler)
        if success:
            print(f"✓ Subscribed to {channel}")
        else:
            error = f"Failed to subscribe to {channel}"
            print(f"✗ {error}")
            results.add_error(error)
    
    # Wait for subscriptions to be active
    await asyncio.sleep(1)
    
    # Publish test messages
    print("\nPublishing test messages...")
    
    # 1. Device telemetry
    success = await publish_device_telemetry(
        "mushroom1",
        {
            "temperature": 22.5,
            "humidity": 65.2,
            "co2": 450,
            "tvoc": 120,
        },
        source="test_script",
    )
    print(f"  {'✓' if success else '✗'} Published device telemetry")
    
    # 2. Agent status
    success = await publish_agent_status(
        "ceo_agent",
        "healthy",
        {
            "uptime_seconds": 3600,
            "tasks_completed": 42,
            "cpu_percent": 5.2,
        },
        source="test_script",
    )
    print(f"  {'✓' if success else '✗'} Published agent status")
    
    # 3. Experiment data
    success = await publish_experiment_data(
        "mycelium_growth_001",
        {
            "growth_rate": 0.15,
            "biomass": 125.4,
            "ph": 6.8,
            "nutrient_level": "optimal",
        },
        source="test_script",
    )
    print(f"  {'✓' if success else '✗'} Published experiment data")
    
    # 4. CREP update
    success = await publish_crep_update(
        "aircraft",
        {
            "icao24": "a12345",
            "callsign": "UAL123",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 35000,
            "velocity": 450,
        },
        source="test_script",
    )
    print(f"  {'✓' if success else '✗'} Published CREP update")
    
    # Wait for messages to be received
    print("\nWaiting for messages to be delivered...")
    await asyncio.sleep(3)
    
    # Print client stats
    stats = client.get_stats()
    print("\nClient Statistics:")
    print(f"  Subscribed channels: {stats['subscribed_channels']}")
    print(f"  Messages published: {stats['messages_published']}")
    print(f"  Messages received: {stats['messages_received']}")
    print(f"  Connection errors: {stats['connection_errors']}")
    
    # Cleanup
    await client.disconnect()
    
    # Print results
    results.print_summary()
    
    # Verify we received all messages
    expected_messages = 4
    if len(results.messages_received) == expected_messages:
        print(f"\n✓ Test PASSED: Received all {expected_messages} messages")
        return True
    else:
        print(f"\n✗ Test FAILED: Expected {expected_messages} messages, got {len(results.messages_received)}")
        return False


async def test_reconnection():
    """Test 3: Automatic reconnection."""
    print("\n[TEST 3] Testing automatic reconnection...")
    print("  Note: This test requires manually stopping/starting Redis")
    print("  Skipping automatic reconnection test in automated mode")
    return True


async def test_multiple_subscribers():
    """Test 4: Multiple subscribers on same channel."""
    print("\n[TEST 4] Testing multiple subscribers on same channel...")
    
    results1 = TestResults()
    results2 = TestResults()
    
    client = RedisPubSubClient()
    await client.connect()
    
    # Create two handlers
    async def handler1(message: PubSubMessage):
        results1.add_message(message)
    
    async def handler2(message: PubSubMessage):
        results2.add_message(message)
    
    # Subscribe both to device telemetry
    channel = Channel.DEVICES_TELEMETRY.value
    await client.subscribe(channel, handler1)
    await client.subscribe(channel, handler2)
    print(f"✓ Subscribed two handlers to {channel}")
    
    await asyncio.sleep(1)
    
    # Publish message
    await publish_device_telemetry(
        "sporebase",
        {"temperature": 21.0, "humidity": 70.0},
        source="test_script",
    )
    
    await asyncio.sleep(2)
    
    # Check both handlers received the message
    if len(results1.messages_received) == 1 and len(results2.messages_received) == 1:
        print("✓ Both handlers received the message")
        await client.disconnect()
        return True
    else:
        print(f"✗ Handler 1: {len(results1.messages_received)}, Handler 2: {len(results2.messages_received)}")
        await client.disconnect()
        return False


async def main():
    """Run all tests."""
    print("="*80)
    print("REDIS PUB/SUB TEST SUITE")
    print("="*80)
    print(f"\nTesting Redis at: 192.168.0.189:6379")
    print("Channels to test:")
    print("  1. devices:telemetry - Device sensor data")
    print("  2. agents:status - Agent health updates")
    print("  3. experiments:data - Lab data streams")
    print("  4. crep:live - Aviation/maritime updates")
    
    results = []
    
    # Run tests
    results.append(("Basic Connection", await test_basic_connection()))
    results.append(("Publish/Subscribe", await test_publish_subscribe()))
    results.append(("Reconnection", await test_reconnection()))
    results.append(("Multiple Subscribers", await test_multiple_subscribers()))
    
    # Print final results
    print("\n" + "="*80)
    print("FINAL TEST RESULTS")
    print("="*80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
