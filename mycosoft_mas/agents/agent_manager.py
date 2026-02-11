import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv
from enum import Enum

from mycosoft_mas.agents.enums import AgentStatus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agent_manager")

class LLMProvider(Enum):
    """Enum for LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    META_LLAMA = "meta_llama"
    CUSTOM = "custom"

class AgentManager:
    """
    Agent Manager - Handles agent lifecycle, customization, and integration with various LLM models.
    Provides debugging, error correction, and auto-heuristics capabilities.
    """
    
    def __init__(self, start_background_tasks: bool = False):
        """Initialize the Agent Manager."""
        self.agents = {}  # Dictionary of agents by ID
        self.agent_configs = {}  # Dictionary of agent configurations
        self.llm_providers = {}  # Dictionary of LLM providers
        self.user_profiles = {}  # Dictionary of user profiles
        self.department_configs = {}  # Dictionary of department configurations
        self.application_configs = {}  # Dictionary of application configurations
        self.device_configs = {}  # Dictionary of device configurations
        self.notification_queue = asyncio.Queue()  # Queue for notifications
        self.error_log = []  # List of errors for debugging
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.debounce_timers = {}  # Dictionary of debounce timers
        self.auto_heuristics = {}  # Dictionary of auto-heuristics
        
        # In unit tests we pass `start_background_tasks=False` and expect a
        # clean in-memory manager with no file/env side effects.
        self._test_mode = not start_background_tasks
        if not self._test_mode:
            # Load configurations
            self._load_configurations()
            # Initialize LLM providers
            self._init_llm_providers()
        
        # Do not auto-start background tasks in __init__ (unit-test friendly).
        self._start_background_tasks_requested = start_background_tasks
    
    def _load_configurations(self):
        """Load configurations from environment variables and files."""
        try:
            # Load user profiles
            user_profiles_path = os.getenv("USER_PROFILES_PATH", "config/user_profiles.json")
            if os.path.exists(user_profiles_path):
                with open(user_profiles_path, "r") as f:
                    self.user_profiles = json.load(f)
            
            # Load department configurations
            department_configs_path = os.getenv("DEPARTMENT_CONFIGS_PATH", "config/department_configs.json")
            if os.path.exists(department_configs_path):
                with open(department_configs_path, "r") as f:
                    self.department_configs = json.load(f)
            
            # Load application configurations
            application_configs_path = os.getenv("APPLICATION_CONFIGS_PATH", "config/application_configs.json")
            if os.path.exists(application_configs_path):
                with open(application_configs_path, "r") as f:
                    self.application_configs = json.load(f)
            
            # Load device configurations
            device_configs_path = os.getenv("DEVICE_CONFIGS_PATH", "config/device_configs.json")
            if os.path.exists(device_configs_path):
                with open(device_configs_path, "r") as f:
                    self.device_configs = json.load(f)
            
            # Load agent configurations
            agent_configs_path = os.getenv("AGENT_CONFIGS_PATH", "config/agent_configs.json")
            if os.path.exists(agent_configs_path):
                with open(agent_configs_path, "r") as f:
                    self.agent_configs = json.load(f)
            
            logger.info("Configurations loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            self._log_error("Configuration loading error", str(e))
    
    def _init_llm_providers(self):
        """Initialize LLM providers."""
        try:
            # OpenAI
            if os.getenv("OPENAI_API_KEY"):
                self.llm_providers[LLMProvider.OPENAI] = {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "models": ["gpt-4", "gpt-3.5-turbo"],
                    "default_model": os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
                }
            
            # Anthropic
            if os.getenv("ANTHROPIC_API_KEY"):
                self.llm_providers[LLMProvider.ANTHROPIC] = {
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                    "default_model": os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-3-sonnet")
                }
            
            # Perplexity
            if os.getenv("PERPLEXITY_API_KEY"):
                self.llm_providers[LLMProvider.PERPLEXITY] = {
                    "api_key": os.getenv("PERPLEXITY_API_KEY"),
                    "models": ["pplx-7b-online", "pplx-70b-online", "pplx-7b-chat"],
                    "default_model": os.getenv("PERPLEXITY_DEFAULT_MODEL", "pplx-7b-chat")
                }
            
            # Meta Llama
            if os.getenv("META_LLAMA_API_KEY"):
                self.llm_providers[LLMProvider.META_LLAMA] = {
                    "api_key": os.getenv("META_LLAMA_API_KEY"),
                    "models": ["llama-2-70b", "llama-2-13b", "llama-2-7b"],
                    "default_model": os.getenv("META_LLAMA_DEFAULT_MODEL", "llama-2-13b")
                }
            
            # Custom provider
            custom_provider_path = os.getenv("CUSTOM_LLM_PROVIDER_PATH")
            if custom_provider_path and os.path.exists(custom_provider_path):
                with open(custom_provider_path, "r") as f:
                    custom_provider = json.load(f)
                    self.llm_providers[LLMProvider.CUSTOM] = custom_provider
            
            logger.info(f"Initialized {len(self.llm_providers)} LLM providers")
        except Exception as e:
            logger.error(f"Error initializing LLM providers: {e}")
            self._log_error("LLM provider initialization error", str(e))
    
    async def initialize(self) -> bool:
        """Test-friendly initialization hook (used by `tests/test_mas.py`)."""
        if getattr(self, "_start_background_tasks_requested", False):
            await self._start_background_tasks()
        return True

    async def list_active_agents(self) -> list[str]:
        """Return a list of active agent ids (used by `tests/test_mas.py`)."""
        active: list[str] = []
        for agent_id, agent in self.agents.items():
            if isinstance(agent, dict):
                if agent.get("status") == AgentStatus.ACTIVE.value:
                    active.append(agent_id)
            else:
                status = getattr(agent, "status", None)
                if getattr(status, "value", status) == AgentStatus.ACTIVE.value:
                    active.append(agent_id)
        return active

    async def _start_background_tasks(self) -> None:
        """Start background tasks (explicit)."""
        self._bg_tasks = [
            asyncio.create_task(self._process_notification_queue()),
            asyncio.create_task(self._monitor_agent_health()),
            asyncio.create_task(self._apply_auto_heuristics()),
        ]
        logger.info("Background tasks started")
    
    async def _process_notification_queue(self):
        """Process the notification queue."""
        while True:
            try:
                notification = await self.notification_queue.get()
                await self._deliver_notification(notification)
                self.notification_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                self._log_error("Notification processing error", str(e))
            await asyncio.sleep(1)
    
    async def _monitor_agent_health(self):
        """Monitor agent health and handle errors."""
        while True:
            try:
                for agent_id, agent in self.agents.items():
                    if agent.get("status") == AgentStatus.ACTIVE.value:
                        # Check agent health
                        if not await self._check_agent_health(agent_id):
                            logger.warning(f"Agent {agent_id} is not healthy")
                            self._log_error(f"Agent {agent_id} health check failed", "Agent not responding")
                            
                            # Apply error correction protocol
                            await self._apply_error_correction(agent_id)
            except Exception as e:
                logger.error(f"Error monitoring agent health: {e}")
                self._log_error("Agent health monitoring error", str(e))
            await asyncio.sleep(60)  # Check every minute
    
    async def _apply_auto_heuristics(self):
        """Apply auto-heuristics to improve agent performance."""
        while True:
            try:
                for agent_id, heuristics in self.auto_heuristics.items():
                    if agent_id in self.agents and self.agents[agent_id].get("status") == AgentStatus.ACTIVE.value:
                        # Apply heuristics
                        await self._apply_heuristics(agent_id, heuristics)
            except Exception as e:
                logger.error(f"Error applying auto-heuristics: {e}")
                self._log_error("Auto-heuristics application error", str(e))
            await asyncio.sleep(300)  # Apply every 5 minutes
    
    async def _check_agent_health(self, agent_id: str) -> bool:
        """Check if an agent is healthy."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            
            # Check if agent has a health check method
            if hasattr(agent.get("instance"), "health_check"):
                return await agent["instance"].health_check()
            
            # Default health check
            return True
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            return False
    
    async def _apply_error_correction(self, agent_id: str):
        """Apply error correction protocol to an agent."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return
            
            # Set agent status to debugging
            agent["status"] = AgentStatus.ACTIVE.value
            
            # Log the error
            self._log_error(f"Agent {agent_id} error correction", "Applying error correction protocol")
            
            # Restart the agent
            await self.restart_agent(agent_id)
            
            # If restart fails, try to recreate the agent
            if agent["status"] != AgentStatus.ACTIVE.value:
                await self.recreate_agent(agent_id)
            
            logger.info(f"Error correction applied to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error applying error correction: {e}")
            self._log_error("Error correction application error", str(e))
    
    async def _apply_heuristics(self, agent_id: str, heuristics: Dict[str, Any]):
        """Apply heuristics to an agent."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return
            
            # Apply each heuristic
            for heuristic_name, heuristic_config in heuristics.items():
                if heuristic_name == "performance_optimization":
                    await self._optimize_agent_performance(agent_id, heuristic_config)
                elif heuristic_name == "resource_management":
                    await self._manage_agent_resources(agent_id, heuristic_config)
                elif heuristic_name == "learning_improvement":
                    await self._improve_agent_learning(agent_id, heuristic_config)
            
            logger.info(f"Heuristics applied to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error applying heuristics: {e}")
            self._log_error("Heuristics application error", str(e))
    
    async def _optimize_agent_performance(self, agent_id: str, config: Dict[str, Any]):
        """Optimize agent performance."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return
            
            # Apply performance optimizations
            if "cache_size" in config:
                agent["cache_size"] = config["cache_size"]
            
            if "batch_size" in config:
                agent["batch_size"] = config["batch_size"]
            
            if "concurrency_limit" in config:
                agent["concurrency_limit"] = config["concurrency_limit"]
            
            logger.info(f"Performance optimizations applied to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error optimizing agent performance: {e}")
    
    async def _manage_agent_resources(self, agent_id: str, config: Dict[str, Any]):
        """Manage agent resources."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return
            
            # Apply resource management
            if "memory_limit" in config:
                agent["memory_limit"] = config["memory_limit"]
            
            if "cpu_limit" in config:
                agent["cpu_limit"] = config["cpu_limit"]
            
            if "gpu_limit" in config:
                agent["gpu_limit"] = config["gpu_limit"]
            
            logger.info(f"Resource management applied to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error managing agent resources: {e}")
    
    async def _improve_agent_learning(self, agent_id: str, config: Dict[str, Any]):
        """Improve agent learning."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return
            
            # Apply learning improvements
            if "learning_rate" in config:
                agent["learning_rate"] = config["learning_rate"]
            
            if "exploration_rate" in config:
                agent["exploration_rate"] = config["exploration_rate"]
            
            if "model_update_frequency" in config:
                agent["model_update_frequency"] = config["model_update_frequency"]
            
            logger.info(f"Learning improvements applied to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error improving agent learning: {e}")
    
    async def _deliver_notification(self, notification: Dict[str, Any]):
        """Deliver a notification to the appropriate recipient."""
        try:
            recipient_id = notification.get("recipient_id")
            notification_type = notification.get("type", "info")
            message = notification.get("message", "")
            priority = notification.get("priority", "normal")
            
            # Get recipient profile
            recipient = self.user_profiles.get(recipient_id)
            if not recipient:
                logger.warning(f"Recipient {recipient_id} not found")
                return
            
            # Check recipient presence
            presence = recipient.get("presence", {})
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Check if recipient is available based on presence
            is_available = True
            if "schedule" in presence:
                schedule = presence["schedule"]
                current_day = current_time.strftime("%A").lower()
                
                if current_day in schedule:
                    day_schedule = schedule[current_day]
                    for time_range in day_schedule:
                        start_hour = time_range.get("start", 0)
                        end_hour = time_range.get("end", 24)
                        activity = time_range.get("activity", "unknown")
                        
                        if start_hour <= current_hour < end_hour:
                            # Check if activity allows notifications
                            if activity in ["sleeping", "meeting", "focus"] and priority != "high":
                                is_available = False
                                break
            
            # If recipient is not available and notification is not high priority, delay it
            if not is_available and priority != "high":
                # Calculate delay until next available time
                delay = self._calculate_notification_delay(recipient)
                if delay > 0:
                    logger.info(f"Delaying notification for {recipient_id} by {delay} seconds")
                    await asyncio.sleep(delay)
            
            # Deliver notification based on preferences
            preferences = recipient.get("notification_preferences", {})
            
            # Text notification
            if preferences.get("text", True):
                await self._send_text_notification(recipient_id, message)
            
            # Voice notification
            if preferences.get("voice", False):
                await self._send_voice_notification(recipient_id, message)
            
            # Email notification
            if preferences.get("email", False):
                await self._send_email_notification(recipient_id, message)
            
            # Discord notification
            if preferences.get("discord", False):
                await self._send_discord_notification(recipient_id, message)
            
            logger.info(f"Notification delivered to {recipient_id}")
        except Exception as e:
            logger.error(f"Error delivering notification: {e}")
            self._log_error("Notification delivery error", str(e))
    
    def _calculate_notification_delay(self, recipient: Dict[str, Any]) -> int:
        """Calculate delay until next available time for notification."""
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            current_day = current_time.strftime("%A").lower()
            
            if "schedule" in recipient.get("presence", {}):
                schedule = recipient["presence"]["schedule"]
                
                if current_day in schedule:
                    day_schedule = schedule[current_day]
                    
                    # Find next available time
                    for time_range in day_schedule:
                        start_hour = time_range.get("start", 0)
                        end_hour = time_range.get("end", 24)
                        activity = time_range.get("activity", "unknown")
                        
                        if activity not in ["sleeping", "meeting", "focus"] and start_hour > current_hour:
                            # Calculate delay in seconds
                            delay_hours = start_hour - current_hour
                            return delay_hours * 3600
            
            # Default delay: 1 hour
            return 3600
        except Exception as e:
            logger.error(f"Error calculating notification delay: {e}")
            return 3600  # Default delay: 1 hour
    
    async def _send_text_notification(self, recipient_id: str, message: str):
        """Send a text notification."""
        # Implementation depends on the text notification service
        logger.info(f"Text notification sent to {recipient_id}: {message}")
    
    async def _send_voice_notification(self, recipient_id: str, message: str):
        """Send a voice notification."""
        # Implementation depends on the voice notification service
        logger.info(f"Voice notification sent to {recipient_id}: {message}")
    
    async def _send_email_notification(self, recipient_id: str, message: str):
        """Send an email notification."""
        # Implementation depends on the email service
        logger.info(f"Email notification sent to {recipient_id}: {message}")
    
    async def _send_discord_notification(self, recipient_id: str, message: str):
        """Send a Discord notification."""
        # Implementation depends on the Discord API
        logger.info(f"Discord notification sent to {recipient_id}: {message}")
    
    def _log_error(self, error_type: str, error_message: str):
        """Log an error for debugging."""
        error = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message
        }
        self.error_log.append(error)
        
        # Keep only the last 1000 errors
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-1000:]

    # ------------------------------------------------------------------
    # Test/legacy-friendly agent lifecycle helpers
    # ------------------------------------------------------------------

    async def register_agent(self, agent: Any) -> None:
        """Register an already-instantiated agent (pytest compatibility)."""
        agent_id = str(getattr(agent, "agent_id", "") or "")
        if not agent_id:
            raise ValueError("agent.agent_id is required")
        self.agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> Any:
        """Return the agent instance for an id (pytest expects sync)."""
        value = self.agents.get(agent_id)
        if isinstance(value, dict) and "instance" in value:
            return value.get("instance")
        return value

    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the manager (pytest compatibility)."""
        value = self.agents.get(agent_id)
        if value is None:
            return False

        try:
            if isinstance(value, dict):
                inst = value.get("instance")
                if inst and hasattr(inst, "shutdown"):
                    await inst.shutdown()
                elif inst and hasattr(inst, "stop"):
                    await inst.stop()
            else:
                if hasattr(value, "shutdown"):
                    await value.shutdown()
                elif hasattr(value, "stop"):
                    await value.stop()
        finally:
            self.agents.pop(agent_id, None)
            self.auto_heuristics.pop(agent_id, None)
        return True
    
    async def create_agent(self, agent_type: str, config: Dict[str, Any]) -> str:
        """
        Create a new agent.
        
        Args:
            agent_type: Type of agent to create
            config: Agent configuration
            
        Returns:
            Agent ID
        """
        try:
            # Generate agent ID
            agent_id = f"{agent_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Get agent configuration
            agent_config = self.agent_configs.get(agent_type, {})
            
            # Merge configurations
            merged_config = {**agent_config, **config}
            
            # Create agent instance
            agent_instance = await self._instantiate_agent(agent_type, merged_config)
            
            # Add agent to dictionary
            self.agents[agent_id] = {
                "id": agent_id,
                "type": agent_type,
                "config": merged_config,
                "instance": agent_instance,
                "status": AgentStatus.ACTIVE.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Initialize auto-heuristics for the agent
            self.auto_heuristics[agent_id] = {
                "performance_optimization": {
                    "cache_size": 1000,
                    "batch_size": 32,
                    "concurrency_limit": 10
                },
                "resource_management": {
                    "memory_limit": "1GB",
                    "cpu_limit": "2",
                    "gpu_limit": "0"
                },
                "learning_improvement": {
                    "learning_rate": 0.001,
                    "exploration_rate": 0.1,
                    "model_update_frequency": 3600
                }
            }
            
            logger.info(f"Agent {agent_id} created successfully")
            return agent_id
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            self._log_error("Agent creation error", str(e))
            return None
    
    async def _instantiate_agent(self, agent_type: str, config: Dict[str, Any]) -> Any:
        """Instantiate an agent based on its type."""
        try:
            # Import the agent class
            module_name = f"mycosoft_mas.agents.{agent_type}_agent"

            def _to_pascal(s: str) -> str:
                return "".join(part.capitalize() for part in s.split("_") if part)

            class_name = f"{_to_pascal(agent_type)}Agent"
            
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Create agent instance
            agent_id = str(config.get("agent_id") or f"{agent_type}_agent")
            name = str(config.get("name") or class_name)
            agent_instance = agent_class(agent_id=agent_id, name=name, config=config)
            
            return agent_instance
        except Exception as e:
            logger.error(f"Error instantiating agent: {e}")
            self._log_error("Agent instantiation error", str(e))
            return None
    
    async def update_agent(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        Update an agent's configuration.
        
        Args:
            agent_id: ID of the agent to update
            config: New agent configuration
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Update agent configuration
            agent["config"].update(config)
            agent["updated_at"] = datetime.now().isoformat()
            
            # Update agent instance
            if hasattr(agent["instance"], "update_config"):
                await agent["instance"].update_config(config)
            
            logger.info(f"Agent {agent_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            self._log_error("Agent update error", str(e))
            return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """
        Restart an agent.
        
        Args:
            agent_id: ID of the agent to restart
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Stop agent
            if hasattr(agent["instance"], "stop"):
                await agent["instance"].stop()
            
            # Start agent
            if hasattr(agent["instance"], "start"):
                await agent["instance"].start()
            
            # Update agent status
            agent["status"] = AgentStatus.ACTIVE.value
            agent["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Agent {agent_id} restarted successfully")
            return True
        except Exception as e:
            logger.error(f"Error restarting agent: {e}")
            self._log_error("Agent restart error", str(e))
            return False
    
    async def recreate_agent(self, agent_id: str) -> bool:
        """
        Recreate an agent.
        
        Args:
            agent_id: ID of the agent to recreate
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Get agent type and configuration
            agent_type = agent["type"]
            config = agent["config"]
            
            # Stop agent
            if hasattr(agent["instance"], "stop"):
                await agent["instance"].stop()
            
            # Create new agent instance
            new_instance = await self._instantiate_agent(agent_type, config)
            
            # Update agent
            agent["instance"] = new_instance
            agent["status"] = AgentStatus.ACTIVE.value
            agent["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Agent {agent_id} recreated successfully")
            return True
        except Exception as e:
            logger.error(f"Error recreating agent: {e}")
            self._log_error("Agent recreation error", str(e))
            return False
    
    async def archive_agent(self, agent_id: str) -> bool:
        """
        Archive an agent.
        
        Args:
            agent_id: ID of the agent to archive
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Stop agent
            if hasattr(agent["instance"], "stop"):
                await agent["instance"].stop()
            
            # Update agent status
            agent["status"] = AgentStatus.SHUTDOWN.value
            agent["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Agent {agent_id} archived successfully")
            return True
        except Exception as e:
            logger.error(f"Error archiving agent: {e}")
            self._log_error("Agent archive error", str(e))
            return False
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent.
        
        Args:
            agent_id: ID of the agent to delete
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Stop agent
            if hasattr(agent["instance"], "stop"):
                await agent["instance"].stop()
            
            # Remove agent from dictionary
            del self.agents[agent_id]
            
            # Remove agent auto-heuristics
            if agent_id in self.auto_heuristics:
                del self.auto_heuristics[agent_id]
            
            logger.info(f"Agent {agent_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            self._log_error("Agent deletion error", str(e))
            return False
    
    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: ID of the agent to get
            
        Returns:
            Agent information
        """
        value = self.agents.get(agent_id, {})
        if not isinstance(value, dict):
            # Normalize to dict shape for older async call sites.
            return {"id": agent_id, "instance": value}
        return value
    
    async def get_agents(self, agent_type: Optional[str] = None, status: Optional[AgentStatus] = None) -> List[Dict[str, Any]]:
        """
        Get agents by type and status.
        
        Args:
            agent_type: Type of agents to get
            status: Status of agents to get
            
        Returns:
            List of agents
        """
        filtered_agents = []
        
        for agent_id, agent in self.agents.items():
            if agent_type and agent["type"] != agent_type:
                continue
            
            if status and agent["status"] != status.value:
                continue
            
            filtered_agents.append(agent)
        
        return filtered_agents
    
    async def get_agent_status(self, agent_id: str) -> str:
        """
        Get an agent's status.
        
        Args:
            agent_id: ID of the agent to get status for
            
        Returns:
            Agent status
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return AgentStatus.IDLE.value
        
        return agent["status"]
    
    async def set_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Set an agent's status.
        
        Args:
            agent_id: ID of the agent to set status for
            status: New agent status
            
        Returns:
            Success status
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Update agent status
            agent["status"] = status.value
            agent["updated_at"] = datetime.now().isoformat()
            
            # Start or stop agent based on status
            if status == AgentStatus.ACTIVE:
                if hasattr(agent["instance"], "start"):
                    await agent["instance"].start()
            elif status == AgentStatus.IDLE:
                if hasattr(agent["instance"], "stop"):
                    await agent["instance"].stop()
            
            logger.info(f"Agent {agent_id} status set to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Error setting agent status: {e}")
            self._log_error("Agent status setting error", str(e))
            return False
    
    async def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get an agent's configuration.
        
        Args:
            agent_id: ID of the agent to get configuration for
            
        Returns:
            Agent configuration
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {}
        
        return agent["config"]
    
    async def get_agent_auto_heuristics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get an agent's auto-heuristics.
        
        Args:
            agent_id: ID of the agent to get auto-heuristics for
            
        Returns:
            Agent auto-heuristics
        """
        return self.auto_heuristics.get(agent_id, {})
    
    async def update_agent_auto_heuristics(self, agent_id: str, heuristics: Dict[str, Any]) -> bool:
        """
        Update an agent's auto-heuristics.
        
        Args:
            agent_id: ID of the agent to update auto-heuristics for
            heuristics: New auto-heuristics
            
        Returns:
            Success status
        """
        try:
            if agent_id not in self.auto_heuristics:
                self.auto_heuristics[agent_id] = {}
            
            # Update auto-heuristics
            self.auto_heuristics[agent_id].update(heuristics)
            
            logger.info(f"Agent {agent_id} auto-heuristics updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating agent auto-heuristics: {e}")
            self._log_error("Agent auto-heuristics update error", str(e))
            return False
    
    async def get_llm_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available LLM providers.
        
        Returns:
            Dictionary of LLM providers
        """
        return {provider.value: config for provider, config in self.llm_providers.items()}
    
    async def get_llm_provider(self, provider: Union[LLMProvider, str]) -> Dict[str, Any]:
        """
        Get an LLM provider by name.
        
        Args:
            provider: LLM provider name or enum
            
        Returns:
            LLM provider configuration
        """
        if isinstance(provider, str):
            provider = LLMProvider(provider)
        
        return self.llm_providers.get(provider, {})
    
    async def add_llm_provider(self, provider: Union[LLMProvider, str], config: Dict[str, Any]) -> bool:
        """
        Add a new LLM provider.
        
        Args:
            provider: LLM provider name or enum
            config: LLM provider configuration
            
        Returns:
            Success status
        """
        try:
            if isinstance(provider, str):
                provider = LLMProvider(provider)
            
            self.llm_providers[provider] = config
            
            logger.info(f"LLM provider {provider.value} added successfully")
            return True
        except Exception as e:
            logger.error(f"Error adding LLM provider: {e}")
            self._log_error("LLM provider addition error", str(e))
            return False
    
    async def remove_llm_provider(self, provider: Union[LLMProvider, str]) -> bool:
        """
        Remove an LLM provider.
        
        Args:
            provider: LLM provider name or enum
            
        Returns:
            Success status
        """
        try:
            if isinstance(provider, str):
                provider = LLMProvider(provider)
            
            if provider in self.llm_providers:
                del self.llm_providers[provider]
                
                logger.info(f"LLM provider {provider.value} removed successfully")
                return True
            else:
                logger.warning(f"LLM provider {provider.value} not found")
                return False
        except Exception as e:
            logger.error(f"Error removing LLM provider: {e}")
            self._log_error("LLM provider removal error", str(e))
            return False
    
    async def get_user_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all user profiles.
        
        Returns:
            Dictionary of user profiles
        """
        return self.user_profiles
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user profile by ID.
        
        Args:
            user_id: ID of the user to get profile for
            
        Returns:
            User profile
        """
        return self.user_profiles.get(user_id, {})
    
    async def update_user_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """
        Update a user profile.
        
        Args:
            user_id: ID of the user to update profile for
            profile: New user profile
            
        Returns:
            Success status
        """
        try:
            self.user_profiles[user_id] = profile
            
            # Save user profiles to file
            user_profiles_path = os.getenv("USER_PROFILES_PATH", "config/user_profiles.json")
            os.makedirs(os.path.dirname(user_profiles_path), exist_ok=True)
            
            with open(user_profiles_path, "w") as f:
                json.dump(self.user_profiles, f, indent=2)
            
            logger.info(f"User profile {user_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            self._log_error("User profile update error", str(e))
            return False
    
    async def get_department_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all department configurations.
        
        Returns:
            Dictionary of department configurations
        """
        return self.department_configs
    
    async def get_department_config(self, department_id: str) -> Dict[str, Any]:
        """
        Get a department configuration by ID.
        
        Args:
            department_id: ID of the department to get configuration for
            
        Returns:
            Department configuration
        """
        return self.department_configs.get(department_id, {})
    
    async def update_department_config(self, department_id: str, config: Dict[str, Any]) -> bool:
        """
        Update a department configuration.
        
        Args:
            department_id: ID of the department to update configuration for
            config: New department configuration
            
        Returns:
            Success status
        """
        try:
            self.department_configs[department_id] = config
            
            # Save department configurations to file
            department_configs_path = os.getenv("DEPARTMENT_CONFIGS_PATH", "config/department_configs.json")
            os.makedirs(os.path.dirname(department_configs_path), exist_ok=True)
            
            with open(department_configs_path, "w") as f:
                json.dump(self.department_configs, f, indent=2)
            
            logger.info(f"Department configuration {department_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating department configuration: {e}")
            self._log_error("Department configuration update error", str(e))
            return False
    
    async def get_application_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all application configurations.
        
        Returns:
            Dictionary of application configurations
        """
        return self.application_configs
    
    async def get_application_config(self, application_id: str) -> Dict[str, Any]:
        """
        Get an application configuration by ID.
        
        Args:
            application_id: ID of the application to get configuration for
            
        Returns:
            Application configuration
        """
        return self.application_configs.get(application_id, {})
    
    async def update_application_config(self, application_id: str, config: Dict[str, Any]) -> bool:
        """
        Update an application configuration.
        
        Args:
            application_id: ID of the application to update configuration for
            config: New application configuration
            
        Returns:
            Success status
        """
        try:
            self.application_configs[application_id] = config
            
            # Save application configurations to file
            application_configs_path = os.getenv("APPLICATION_CONFIGS_PATH", "config/application_configs.json")
            os.makedirs(os.path.dirname(application_configs_path), exist_ok=True)
            
            with open(application_configs_path, "w") as f:
                json.dump(self.application_configs, f, indent=2)
            
            logger.info(f"Application configuration {application_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating application configuration: {e}")
            self._log_error("Application configuration update error", str(e))
            return False
    
    async def get_device_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all device configurations.
        
        Returns:
            Dictionary of device configurations
        """
        return self.device_configs
    
    async def get_device_config(self, device_id: str) -> Dict[str, Any]:
        """
        Get a device configuration by ID.
        
        Args:
            device_id: ID of the device to get configuration for
            
        Returns:
            Device configuration
        """
        return self.device_configs.get(device_id, {})
    
    async def update_device_config(self, device_id: str, config: Dict[str, Any]) -> bool:
        """
        Update a device configuration.
        
        Args:
            device_id: ID of the device to update configuration for
            config: New device configuration
            
        Returns:
            Success status
        """
        try:
            self.device_configs[device_id] = config
            
            # Save device configurations to file
            device_configs_path = os.getenv("DEVICE_CONFIGS_PATH", "config/device_configs.json")
            os.makedirs(os.path.dirname(device_configs_path), exist_ok=True)
            
            with open(device_configs_path, "w") as f:
                json.dump(self.device_configs, f, indent=2)
            
            logger.info(f"Device configuration {device_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating device configuration: {e}")
            self._log_error("Device configuration update error", str(e))
            return False
    
    async def get_error_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the error log.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of errors
        """
        return self.error_log[-limit:]
    
    async def clear_error_log(self) -> bool:
        """
        Clear the error log.
        
        Returns:
            Success status
        """
        try:
            self.error_log = []
            logger.info("Error log cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing error log: {e}")
            return False
    
    async def send_notification(self, recipient_id: str, message: str, notification_type: str = "info", priority: str = "normal") -> bool:
        """
        Send a notification to a user.
        
        Args:
            recipient_id: ID of the recipient
            message: Notification message
            notification_type: Type of notification
            priority: Notification priority
            
        Returns:
            Success status
        """
        try:
            notification = {
                "recipient_id": recipient_id,
                "message": message,
                "type": notification_type,
                "priority": priority,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.notification_queue.put(notification)
            
            logger.info(f"Notification queued for {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            self._log_error("Notification sending error", str(e))
            return False
    
    async def get_notification_queue_size(self) -> int:
        """
        Get the size of the notification queue.
        
        Returns:
            Queue size
        """
        return self.notification_queue.qsize()
    
    async def set_debug_mode(self, enabled: bool) -> bool:
        """
        Set debug mode.
        
        Args:
            enabled: Whether to enable debug mode
            
        Returns:
            Success status
        """
        try:
            self.debug_mode = enabled
            logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error setting debug mode: {e}")
            return False
    
    async def get_debug_mode(self) -> bool:
        """
        Get debug mode status.
        
        Returns:
            Debug mode status
        """
        return self.debug_mode
    
    async def debounce(self, key: str, delay: float = 1.0) -> bool:
        """
        Debounce a function call.
        
        Args:
            key: Debounce key
            delay: Debounce delay in seconds
            
        Returns:
            Whether the call should proceed
        """
        try:
            current_time = datetime.now().timestamp()
            
            if key in self.debounce_timers:
                last_time = self.debounce_timers[key]
                
                if current_time - last_time < delay:
                    return False
            
            self.debounce_timers[key] = current_time
            return True
        except Exception as e:
            logger.error(f"Error debouncing: {e}")
            return True  # Proceed on error
    
    async def start(self):
        """Start the Agent Manager."""
        logger.info("Agent Manager started")
    
    async def stop(self):
        """Stop the Agent Manager."""
        # Stop all agents
        for agent_id, agent in list(self.agents.items()):
            try:
                if isinstance(agent, dict):
                    if agent.get("status") == AgentStatus.ACTIVE.value:
                        inst = agent.get("instance")
                        if inst and hasattr(inst, "stop"):
                            await inst.stop()
                        if inst and hasattr(inst, "shutdown"):
                            await inst.shutdown()
                else:
                    if hasattr(agent, "stop"):
                        await agent.stop()
                    if hasattr(agent, "shutdown"):
                        await agent.shutdown()
            except Exception:
                pass
        
        logger.info("Agent Manager stopped")
    
    async def _handle_error_type(self, error_type: str, error_data: Dict) -> Dict:
        """Handle different types of errors that might occur during agent management operations.
        
        Args:
            error_type: The type of error that occurred
            error_data: Additional data about the error
            
        Returns:
            Dict containing error handling results
        """
        try:
            if error_type == "agent_error":
                # Handle agent-related errors
                agent_id = error_data.get('agent_id')
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    agent.status = AgentStatus.ERROR
                    self.logger.warning(f"Agent {agent_id} marked as error: {error_data.get('message')}")
                    return {"success": True, "action": "agent_error", "agent_id": agent_id}
                    
            elif error_type == "communication_error":
                # Handle communication-related errors
                message_id = error_data.get('message_id')
                if message_id in self.messages:
                    message = self.messages[message_id]
                    message.status = MessageStatus.FAILED
                    self.logger.warning(f"Message {message_id} marked as failed: {error_data.get('message')}")
                    return {"success": True, "action": "message_failed", "message_id": message_id}
                    
            elif error_type == "coordination_error":
                # Handle coordination-related errors
                task_id = error_data.get('task_id')
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.FAILED
                    self.logger.warning(f"Task {task_id} marked as failed: {error_data.get('message')}")
                    return {"success": True, "action": "task_failed", "task_id": task_id}
                    
            elif error_type == "api_error":
                # Handle API-related errors
                service = error_data.get('service')
                if service in self.api_clients:
                    # Attempt to reinitialize the API client
                    await self._init_api_connection(service)
                    self.logger.warning(f"API client for {service} reinitialized after error")
                    return {"success": True, "action": "api_reinitialized", "service": service}
                    
            # For unknown error types, log and return generic response
            self.logger.error(f"Unknown error type {error_type}: {error_data}")
            return {
                "success": False,
                "error_type": error_type,
                "message": "Unknown error type encountered"
            }
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return {
                "success": False,
                "error_type": "error_handling_failed",
                "message": str(e)
            } 