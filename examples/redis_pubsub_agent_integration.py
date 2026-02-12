"""
Redis Pub/Sub Agent Integration Example - February 12, 2026

Shows how MAS agents can use Redis pub/sub for real-time communication.
"""

import asyncio
import logging
from typing import Any, Dict

from mycosoft_mas.realtime.redis_pubsub import (
    RedisPubSubClient,
    Channel,
    PubSubMessage,
    publish_agent_status,
    publish_device_telemetry,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleAgent:
    """
    Example agent that uses Redis pub/sub for:
    - Broadcasting its own status
    - Listening for device telemetry
    - Reacting to system events
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.redis_client: RedisPubSubClient = None
        self.is_running = False
        self.device_count = 0
    
    async def start(self):
        """Start the agent and subscribe to channels."""
        logger.info(f"Starting agent {self.agent_id}")
        
        # Connect to Redis
        self.redis_client = RedisPubSubClient()
        connected = await self.redis_client.connect()
        
        if not connected:
            logger.error("Failed to connect to Redis")
            return
        
        # Subscribe to device telemetry
        await self.redis_client.subscribe(
            Channel.DEVICES_TELEMETRY.value,
            self.handle_device_telemetry,
        )
        
        # Subscribe to other agents' status
        await self.redis_client.subscribe(
            Channel.AGENTS_STATUS.value,
            self.handle_agent_status,
        )
        
        logger.info(f"Agent {self.agent_id} subscribed to channels")
        
        # Publish initial status
        await self.broadcast_status("healthy", "Agent started")
        
        self.is_running = True
    
    async def stop(self):
        """Stop the agent and cleanup."""
        logger.info(f"Stopping agent {self.agent_id}")
        
        # Publish shutdown status
        await self.broadcast_status("shutdown", "Agent stopping")
        
        # Disconnect from Redis
        if self.redis_client:
            await self.redis_client.disconnect()
        
        self.is_running = False
    
    async def broadcast_status(self, status: str, message: str):
        """Broadcast agent status via Redis pub/sub."""
        await publish_agent_status(
            agent_id=self.agent_id,
            status=status,
            details={
                "message": message,
                "device_count": self.device_count,
            },
            source=self.agent_id,
        )
        logger.info(f"Broadcasted status: {status} - {message}")
    
    async def handle_device_telemetry(self, message: PubSubMessage):
        """
        Handle incoming device telemetry.
        
        This is called automatically when a device publishes telemetry.
        """
        device_id = message.data.get("device_id")
        telemetry = message.data.get("telemetry", {})
        
        logger.info(f"Received telemetry from {device_id}: {telemetry}")
        
        self.device_count += 1
        
        # Example: Check for alerts
        temp = telemetry.get("temperature")
        if temp and temp > 30.0:
            logger.warning(f"High temperature alert for {device_id}: {temp}°C")
            await self.broadcast_status(
                "alert",
                f"High temperature detected: {temp}°C on {device_id}"
            )
    
    async def handle_agent_status(self, message: PubSubMessage):
        """
        Handle status updates from other agents.
        
        This allows agents to coordinate and react to each other.
        """
        agent_id = message.data.get("agent_id")
        status = message.data.get("status")
        
        # Ignore our own status messages
        if agent_id == self.agent_id:
            return
        
        logger.info(f"Agent {agent_id} status: {status}")
        
        # Example: React to other agents
        if status == "error":
            logger.warning(f"Agent {agent_id} reported an error")
    
    async def do_work(self):
        """
        Example work loop.
        
        Periodically broadcasts status and processes data.
        """
        iteration = 0
        
        while self.is_running:
            iteration += 1
            
            # Simulate work
            await asyncio.sleep(5)
            
            # Broadcast periodic heartbeat
            await self.broadcast_status(
                "healthy",
                f"Heartbeat #{iteration}"
            )


async def main():
    """Example usage."""
    
    # Create agent
    agent = ExampleAgent("example_agent_001")
    
    # Start agent
    await agent.start()
    
    # Simulate external device telemetry
    await asyncio.sleep(2)
    
    logger.info("Simulating device telemetry...")
    await publish_device_telemetry(
        device_id="mushroom1",
        telemetry={
            "temperature": 22.5,
            "humidity": 65.2,
            "co2": 450,
        },
        source="simulator",
    )
    
    await asyncio.sleep(2)
    
    # Simulate high temperature alert
    logger.info("Simulating high temperature...")
    await publish_device_telemetry(
        device_id="sporebase",
        telemetry={
            "temperature": 35.0,  # High!
            "humidity": 70.0,
        },
        source="simulator",
    )
    
    # Let agent do some work
    work_task = asyncio.create_task(agent.do_work())
    
    # Run for a while
    await asyncio.sleep(10)
    
    # Stop agent
    work_task.cancel()
    await agent.stop()
    
    logger.info("Example complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
