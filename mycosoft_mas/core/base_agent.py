"""
Base Agent class for Mycosoft MAS
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
import asyncio
from ..services.integration_service import IntegrationService

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all agents in the Mycosoft MAS."""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary for the agent
        """
        self.agent_id = agent_id
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.integration_service: Optional[IntegrationService] = None
        self.status = "initialized"
        self.metrics = {
            "messages_processed": 0,
            "errors": 0,
            "last_activity": None,
            "uptime": 0
        }
        self.notification_queue = asyncio.Queue()
        
    async def initialize(self, integration_service: IntegrationService):
        """Initialize the agent with required services.
        
        Args:
            integration_service: The integration service instance
        """
        self.integration_service = integration_service
        self.status = "running"
        self.metrics["last_activity"] = datetime.now()
        self.logger.info(f"Agent {self.agent_id} initialized successfully")
        
    async def shutdown(self):
        """Shutdown the agent and clean up resources."""
        self.status = "stopped"
        self.logger.info(f"Agent {self.agent_id} shut down successfully")
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message.
        
        Args:
            message: The message to process
            
        Returns:
            Dict containing the response
        """
        try:
            self.metrics["messages_processed"] += 1
            self.metrics["last_activity"] = datetime.now()
            
            # Update message status
            message["status"] = "processing"
            message["processed_at"] = datetime.now().isoformat()
            
            # Process the message
            response = await self._handle_message(message)
            
            # Update message status
            message["status"] = "completed"
            message["completed_at"] = datetime.now().isoformat()
            
            return response
            
        except Exception as e:
            self.metrics["errors"] += 1
            self.logger.error(f"Error processing message: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process message: {str(e)}"
            }
            
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the message processing logic.
        
        Args:
            message: The message to process
            
        Returns:
            Dict containing the response
        """
        raise NotImplementedError("Subclasses must implement _handle_message")
        
    async def _start_background_tasks(self):
        """Start any background tasks needed by the agent."""
        pass
        
    async def _handle_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors that occur during message processing.
        
        Args:
            error: The error information
            
        Returns:
            Dict containing the error handling response
        """
        try:
            error_type = error.get("type", "unknown")
            error_data = error.get("data", {})
            
            # Log the error
            self.logger.error(f"Error type {error_type}: {error_data}")
            
            # Update metrics
            self.metrics["errors"] += 1
            
            # Handle specific error types
            if error_type == "connection_error":
                return await self._handle_connection_error(error_data)
            elif error_type == "validation_error":
                return await self._handle_validation_error(error_data)
            elif error_type == "processing_error":
                return await self._handle_processing_error(error_data)
            else:
                return {
                    "status": "error",
                    "message": f"Unhandled error type: {error_type}",
                    "error_data": error_data
                }
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {
                "status": "error",
                "message": f"Error handler failed: {str(e)}"
            }
            
    async def _handle_connection_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection-related errors."""
        return {
            "status": "error",
            "message": "Connection error occurred",
            "error_data": error_data,
            "action": "retry_connection"
        }
        
    async def _handle_validation_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation-related errors."""
        return {
            "status": "error",
            "message": "Validation error occurred",
            "error_data": error_data,
            "action": "validate_input"
        }
        
    async def _handle_processing_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle processing-related errors."""
        return {
            "status": "error",
            "message": "Processing error occurred",
            "error_data": error_data,
            "action": "retry_processing"
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metrics for the agent.
        
        Returns:
            Dict containing the agent metrics
        """
        return {
            **self.metrics,
            "status": self.status,
            "uptime": (datetime.now() - self.metrics["last_activity"]).total_seconds() if self.metrics["last_activity"] else 0
        } 