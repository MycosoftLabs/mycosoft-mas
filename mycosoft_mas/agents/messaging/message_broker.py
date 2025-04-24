"""
Message Broker for Mycosoft MAS

This module implements a simple in-memory message broker for the Mycosoft MAS.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

class MessageBroker:
    """Simple in-memory message broker."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the message broker."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.queue = asyncio.Queue()
        self.status = "initialized"
        self.metrics = {
            "messages_processed": 0,
            "errors": 0
        }
    
    async def start(self) -> None:
        """Start the message broker."""
        self.logger.info("Starting message broker")
        self.status = "running"
        asyncio.create_task(self._process_queue())
    
    async def stop(self) -> None:
        """Stop the message broker."""
        self.logger.info("Stopping message broker")
        self.status = "stopped"
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the queue."""
        try:
            await self.queue.put(message)
            self.metrics["messages_processed"] += 1
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            self.metrics["errors"] += 1
            return False
    
    async def _process_queue(self) -> None:
        """Process messages in the queue."""
        while True:
            try:
                message = await self.queue.get()
                # Process message here
                self.queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.metrics["errors"] += 1
            await asyncio.sleep(0.1)  # Prevent busy waiting
    
    async def receive_message(self, recipient_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Receive a message for a recipient."""
        try:
            message = await self.queue.get()
            if message.get("recipient_id") == recipient_id:
                return message
            else:
                await self.queue.put(message)  # Put it back if not for this recipient
                return None
        except Exception as e:
            self.logger.error(f"Error receiving message: {str(e)}")
            return None 