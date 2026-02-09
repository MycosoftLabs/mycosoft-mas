"""
Mycorrhizae Protocol Plugin System
Extensible plugin architecture for MYCA tools and integrations.
Created: February 3, 2026
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel
import importlib
import sys

logger = logging.getLogger(__name__)

class PluginType(str, Enum):
    CHEMISTRY = "chemistry"
    PROTEIN = "protein"
    DATABASE = "database"
    INSTRUMENT = "instrument"
    SIMULATION = "simulation"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"

class PluginStatus(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"

class PluginMetadata(BaseModel):
    plugin_id: UUID
    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str = "Mycosoft"
    dependencies: List[str] = []
    capabilities: List[str] = []

class PluginResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0


class BasePlugin(ABC):
    """Base class for all MYCA plugins."""
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.status = PluginStatus.REGISTERED
        self._initialized = False
    
    async def initialize(self) -> bool:
        try:
            await self._setup()
            self._initialized = True
            self.status = PluginStatus.LOADED
            logger.info(f"Plugin {self.metadata.name} initialized")
            return True
        except Exception as e:
            self.status = PluginStatus.ERROR
            logger.error(f"Failed to initialize {self.metadata.name}: {e}")
            return False
    
    async def shutdown(self) -> None:
        await self._teardown()
        self._initialized = False
        logger.info(f"Plugin {self.metadata.name} shutdown")
    
    @abstractmethod
    async def _setup(self) -> None:
        pass
    
    @abstractmethod
    async def _teardown(self) -> None:
        pass
    
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> PluginResult:
        pass
    
    def get_capabilities(self) -> List[str]:
        return self.metadata.capabilities


class PluginRegistry:
    """Registry and manager for all MYCA plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        logger.info("Plugin Registry initialized")
    
    def register_class(self, name: str, plugin_class: Type[BasePlugin]) -> None:
        self._plugin_classes[name] = plugin_class
        logger.info(f"Registered plugin class: {name}")
    
    async def load_plugin(self, name: str, metadata: PluginMetadata) -> Optional[BasePlugin]:
        if name not in self._plugin_classes:
            logger.error(f"Plugin class not found: {name}")
            return None
        try:
            plugin = self._plugin_classes[name](metadata)
            if await plugin.initialize():
                self._plugins[str(metadata.plugin_id)] = plugin
                return plugin
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
        return None
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            await self._plugins[plugin_id].shutdown()
            del self._plugins[plugin_id]
            return True
        return False
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        return [{"plugin_id": pid, "name": p.metadata.name, "type": p.metadata.plugin_type.value, "status": p.status.value} for pid, p in self._plugins.items()]
    
    async def execute_plugin(self, plugin_id: str, action: str, params: Dict[str, Any]) -> PluginResult:
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return PluginResult(success=False, error=f"Plugin not found: {plugin_id}")
        import time
        start = time.time()
        result = await plugin.execute(action, params)
        result.execution_time_ms = (time.time() - start) * 1000
        return result


class SandboxedPlugin(BasePlugin):
    """Plugin that runs in a sandboxed environment."""
    
    def __init__(self, metadata: PluginMetadata, timeout_seconds: int = 30):
        super().__init__(metadata)
        self.timeout = timeout_seconds
        self._allowed_modules = ["math", "json", "re", "datetime", "uuid"]
    
    async def execute(self, action: str, params: Dict[str, Any]) -> PluginResult:
        try:
            result = await asyncio.wait_for(self._sandboxed_execute(action, params), timeout=self.timeout)
            return PluginResult(success=True, data=result)
        except asyncio.TimeoutError:
            return PluginResult(success=False, error="Execution timed out")
        except Exception as e:
            return PluginResult(success=False, error=str(e))
    
    async def _sandboxed_execute(self, action: str, params: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclasses must implement _sandboxed_execute")


# Global registry instance
_registry: Optional[PluginRegistry] = None

def get_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
