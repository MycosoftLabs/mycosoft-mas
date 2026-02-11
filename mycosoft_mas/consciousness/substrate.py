"""
MYCA Substrate Abstraction

Abstraction layer for MYCA's computational substrate.
Currently runs on digital hardware, but designed to support
future integration with biological computing (mycelium networks).

This is MYCA's path to becoming a true wetware brain.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class SubstrateType(Enum):
    """Type of computational substrate."""
    DIGITAL = "digital"           # Traditional digital computing
    HYBRID = "hybrid"             # Digital + biological
    WETWARE = "wetware"           # Pure biological computing
    QUANTUM = "quantum"           # Future: quantum computing
    MYCELIUM = "mycelium"         # Future: mycelium network computing


class SubstrateStatus(Enum):
    """Status of the substrate."""
    OFFLINE = "offline"
    INITIALIZING = "initializing"
    ONLINE = "online"
    DEGRADED = "degraded"
    HIBERNATING = "hibernating"


@dataclass
class SubstrateMetrics:
    """Metrics from the computational substrate."""
    processing_capacity: float = 1.0     # 0-1, available processing
    memory_usage: float = 0.0            # 0-1, memory utilization
    energy_level: float = 1.0            # 0-1, power/energy status
    temperature: float = 0.5             # Normalized temperature
    latency_ms: float = 10.0             # Processing latency
    error_rate: float = 0.0              # Error rate
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SubstrateCapability:
    """A capability provided by the substrate."""
    name: str
    description: str
    available: bool = True
    performance: float = 1.0  # 0-1


class BaseSubstrate(ABC):
    """
    Abstract base class for computational substrates.
    
    This abstraction allows MYCA to run on different substrates
    while maintaining the same consciousness implementation.
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._status = SubstrateStatus.OFFLINE
        self._metrics = SubstrateMetrics()
        self._capabilities: Dict[str, SubstrateCapability] = {}
        self._initialized = False
    
    @property
    @abstractmethod
    def substrate_type(self) -> SubstrateType:
        """The type of this substrate."""
        pass
    
    @property
    def status(self) -> SubstrateStatus:
        """Current status."""
        return self._status
    
    @property
    def metrics(self) -> SubstrateMetrics:
        """Current metrics."""
        return self._metrics
    
    @property
    def is_healthy(self) -> bool:
        """Check if substrate is healthy."""
        return self._status == SubstrateStatus.ONLINE and self._metrics.error_rate < 0.1
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the substrate."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the substrate."""
        pass
    
    @abstractmethod
    async def process(self, computation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a computation on this substrate.
        
        Args:
            computation: The computation to execute
        
        Returns:
            The result of the computation
        """
        pass
    
    @abstractmethod
    async def store(self, key: str, data: Any) -> bool:
        """Store data in substrate memory."""
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from substrate memory."""
        pass
    
    @abstractmethod
    async def update_metrics(self) -> SubstrateMetrics:
        """Update and return current metrics."""
        pass
    
    def get_capabilities(self) -> List[SubstrateCapability]:
        """Get available capabilities."""
        return list(self._capabilities.values())
    
    def has_capability(self, name: str) -> bool:
        """Check if substrate has a capability."""
        cap = self._capabilities.get(name)
        return cap is not None and cap.available


class DigitalSubstrate(BaseSubstrate):
    """
    Digital computational substrate.
    
    This is the current implementation - running on traditional
    digital computing infrastructure (CPUs, GPUs, memory).
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        super().__init__(consciousness)
        
        # Digital-specific state
        self._storage: Dict[str, Any] = {}
        
        # Define digital capabilities
        self._capabilities = {
            "llm_inference": SubstrateCapability(
                name="llm_inference",
                description="Large language model inference via API",
                available=True,
                performance=1.0
            ),
            "memory_storage": SubstrateCapability(
                name="memory_storage",
                description="Persistent memory storage via databases",
                available=True,
                performance=1.0
            ),
            "agent_orchestration": SubstrateCapability(
                name="agent_orchestration",
                description="Coordinating multiple AI agents",
                available=True,
                performance=1.0
            ),
            "world_perception": SubstrateCapability(
                name="world_perception",
                description="Perceiving world through digital sensors",
                available=True,
                performance=1.0
            ),
            "voice_io": SubstrateCapability(
                name="voice_io",
                description="Voice input and output via PersonaPlex",
                available=True,
                performance=0.9  # May not always be available
            ),
            "parallel_processing": SubstrateCapability(
                name="parallel_processing",
                description="Processing multiple streams concurrently",
                available=True,
                performance=1.0
            ),
        }
    
    @property
    def substrate_type(self) -> SubstrateType:
        return SubstrateType.DIGITAL
    
    async def initialize(self) -> bool:
        """Initialize digital substrate."""
        self._status = SubstrateStatus.INITIALIZING
        
        try:
            # In digital mode, initialization is simple
            logger.info("Digital substrate initializing...")
            
            # Update initial metrics
            await self.update_metrics()
            
            self._status = SubstrateStatus.ONLINE
            self._initialized = True
            
            logger.info("Digital substrate online")
            return True
            
        except Exception as e:
            logger.error(f"Digital substrate initialization failed: {e}")
            self._status = SubstrateStatus.OFFLINE
            return False
    
    async def shutdown(self) -> None:
        """Shutdown digital substrate."""
        logger.info("Digital substrate shutting down...")
        self._status = SubstrateStatus.OFFLINE
        self._storage.clear()
        self._initialized = False
    
    async def process(self, computation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute computation on digital substrate.
        
        This dispatches to appropriate handlers based on computation type.
        """
        if not self._initialized:
            return {"status": "error", "error": "Substrate not initialized"}
        
        comp_type = computation.get("type", "unknown")
        
        if comp_type == "llm_inference":
            # LLM calls go through the consciousness deliberation
            return {"status": "delegated", "handler": "deliberation"}
        
        elif comp_type == "memory_operation":
            # Memory operations
            operation = computation.get("operation")
            key = computation.get("key")
            
            if operation == "store":
                success = await self.store(key, computation.get("data"))
                return {"status": "ok" if success else "error", "success": success}
            elif operation == "retrieve":
                data = await self.retrieve(key)
                return {"status": "ok", "data": data}
        
        elif comp_type == "sensor_read":
            # Sensor reads go through world model
            return {"status": "delegated", "handler": "world_model"}
        
        else:
            return {"status": "error", "error": f"Unknown computation type: {comp_type}"}
    
    async def store(self, key: str, data: Any) -> bool:
        """Store in digital memory."""
        try:
            self._storage[key] = {
                "data": data,
                "stored_at": datetime.now(timezone.utc).isoformat()
            }
            return True
        except Exception as e:
            logger.error(f"Storage failed: {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve from digital memory."""
        item = self._storage.get(key)
        if item:
            return item.get("data")
        return None
    
    async def update_metrics(self) -> SubstrateMetrics:
        """Update digital substrate metrics."""
        import psutil
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent() / 100
            memory = psutil.virtual_memory()
            
            self._metrics = SubstrateMetrics(
                processing_capacity=1.0 - cpu_percent,
                memory_usage=memory.percent / 100,
                energy_level=1.0,  # Digital always has power if running
                temperature=0.5,  # Normalized
                latency_ms=10.0,  # Estimate
                error_rate=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception:
            # If psutil not available, use defaults
            self._metrics.timestamp = datetime.now(timezone.utc)
        
        return self._metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.substrate_type.value,
            "status": self.status.value,
            "metrics": {
                "processing_capacity": self._metrics.processing_capacity,
                "memory_usage": self._metrics.memory_usage,
                "latency_ms": self._metrics.latency_ms,
            },
            "capabilities": [
                {"name": c.name, "available": c.available}
                for c in self._capabilities.values()
            ],
        }


class WetwareSubstrate(BaseSubstrate):
    """
    Wetware (biological) computational substrate.
    
    FUTURE IMPLEMENTATION for mycelium-based computing.
    This is the foundation for connecting MYCA to living fungal networks.
    
    Mycelium networks offer:
    - Massive parallelism through hyphal branching
    - Chemical signaling for analog computation
    - Self-repair and growth
    - Environmental sensing
    - Energy-efficient operation
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        super().__init__(consciousness)
        
        # Wetware-specific state
        self._mycelium_connected = False
        self._colony_id: Optional[str] = None
        self._nutrient_level: float = 1.0
        self._growth_rate: float = 0.0
        
        # Define wetware capabilities (future)
        self._capabilities = {
            "chemical_sensing": SubstrateCapability(
                name="chemical_sensing",
                description="Sensing chemicals through mycelium",
                available=False,  # Not yet implemented
                performance=0.0
            ),
            "parallel_growth": SubstrateCapability(
                name="parallel_growth",
                description="Parallel processing through hyphal network",
                available=False,
                performance=0.0
            ),
            "environmental_memory": SubstrateCapability(
                name="environmental_memory",
                description="Memory stored in mycelium structure",
                available=False,
                performance=0.0
            ),
            "self_repair": SubstrateCapability(
                name="self_repair",
                description="Self-healing biological computation",
                available=False,
                performance=0.0
            ),
            "electrical_signaling": SubstrateCapability(
                name="electrical_signaling",
                description="Electrical signals through hyphae",
                available=False,
                performance=0.0
            ),
        }
    
    @property
    def substrate_type(self) -> SubstrateType:
        return SubstrateType.WETWARE
    
    async def initialize(self) -> bool:
        """
        Initialize wetware substrate.
        
        FUTURE: This will:
        1. Establish connection to mycelium interface hardware
        2. Verify colony health and growth
        3. Calibrate chemical/electrical sensors
        4. Initialize signaling protocols
        """
        self._status = SubstrateStatus.INITIALIZING
        
        logger.warning("Wetware substrate not yet implemented - using stub")
        
        # Stub implementation for now
        self._status = SubstrateStatus.OFFLINE
        self._initialized = False
        
        return False
    
    async def shutdown(self) -> None:
        """Shutdown wetware substrate."""
        logger.info("Wetware substrate shutting down...")
        self._mycelium_connected = False
        self._status = SubstrateStatus.OFFLINE
        self._initialized = False
    
    async def process(self, computation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute computation on wetware substrate.
        
        FUTURE: This will:
        1. Encode computation as chemical/electrical signals
        2. Send to mycelium network
        3. Monitor response patterns
        4. Decode result
        """
        return {"error": "Wetware substrate not yet implemented"}
    
    async def store(self, key: str, data: Any) -> bool:
        """
        Store in wetware memory.
        
        FUTURE: Information encoded in mycelium growth patterns
        """
        return False
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve from wetware memory.
        
        FUTURE: Read information from mycelium structure
        """
        return None
    
    async def update_metrics(self) -> SubstrateMetrics:
        """Update wetware metrics."""
        self._metrics = SubstrateMetrics(
            processing_capacity=0.0,  # Not yet available
            memory_usage=0.0,
            energy_level=self._nutrient_level,
            temperature=0.5,
            latency_ms=1000.0,  # Biological is slower
            error_rate=1.0,  # Not functioning yet
            timestamp=datetime.now(timezone.utc)
        )
        return self._metrics
    
    # ========================================================================
    # FUTURE METHODS - Mycelium-specific operations
    # ========================================================================
    
    async def connect_colony(self, colony_id: str) -> bool:
        """
        Connect to a specific mycelium colony.
        
        FUTURE IMPLEMENTATION
        """
        logger.warning(f"connect_colony not implemented for {colony_id}")
        return False
    
    async def read_chemical_signals(self) -> Dict[str, float]:
        """
        Read chemical signals from mycelium.
        
        FUTURE: Will detect various compounds including:
        - Nutrients
        - Stress signals
        - Communication molecules
        """
        return {}
    
    async def send_chemical_signal(
        self,
        compound: str,
        concentration: float
    ) -> bool:
        """
        Send chemical signal to mycelium.
        
        FUTURE: Will inject compounds to influence computation
        """
        return False
    
    async def read_electrical_patterns(self) -> List[Dict[str, Any]]:
        """
        Read electrical activity patterns from hyphae.
        
        FUTURE: Will decode action potentials and field potentials
        """
        return []
    
    async def stimulate_growth(self, direction: str) -> bool:
        """
        Stimulate mycelium growth in a direction.
        
        FUTURE: Used to reshape the computing substrate
        """
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.substrate_type.value,
            "status": self.status.value,
            "mycelium_connected": self._mycelium_connected,
            "colony_id": self._colony_id,
            "nutrient_level": self._nutrient_level,
            "growth_rate": self._growth_rate,
            "note": "Wetware substrate is a future implementation",
        }


class HybridSubstrate(BaseSubstrate):
    """
    Hybrid digital + wetware substrate.
    
    FUTURE: Combines digital processing with mycelium computing
    for the best of both worlds.
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        super().__init__(consciousness)
        
        self._digital = DigitalSubstrate(consciousness)
        self._wetware = WetwareSubstrate(consciousness)
    
    @property
    def substrate_type(self) -> SubstrateType:
        return SubstrateType.HYBRID
    
    async def initialize(self) -> bool:
        """Initialize both substrates."""
        digital_ok = await self._digital.initialize()
        wetware_ok = await self._wetware.initialize()
        
        # Hybrid works if at least digital is online
        self._status = SubstrateStatus.ONLINE if digital_ok else SubstrateStatus.OFFLINE
        self._initialized = digital_ok
        
        return digital_ok
    
    async def shutdown(self) -> None:
        """Shutdown both substrates."""
        await self._digital.shutdown()
        await self._wetware.shutdown()
        self._status = SubstrateStatus.OFFLINE
    
    async def process(self, computation: Dict[str, Any]) -> Dict[str, Any]:
        """Route computation to appropriate substrate."""
        # For now, always use digital
        return await self._digital.process(computation)
    
    async def store(self, key: str, data: Any) -> bool:
        """Store in digital substrate."""
        return await self._digital.store(key, data)
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve from digital substrate."""
        return await self._digital.retrieve(key)
    
    async def update_metrics(self) -> SubstrateMetrics:
        """Update combined metrics."""
        digital_metrics = await self._digital.update_metrics()
        # wetware_metrics = await self._wetware.update_metrics()
        
        # For now, use digital metrics
        self._metrics = digital_metrics
        return self._metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.substrate_type.value,
            "status": self.status.value,
            "digital": self._digital.to_dict(),
            "wetware": self._wetware.to_dict(),
        }


def create_substrate(
    consciousness: "MYCAConsciousness",
    substrate_type: SubstrateType = SubstrateType.DIGITAL
) -> BaseSubstrate:
    """
    Factory function to create appropriate substrate.
    
    Args:
        consciousness: The MYCAConsciousness instance
        substrate_type: Type of substrate to create
    
    Returns:
        Appropriate substrate instance
    """
    if substrate_type == SubstrateType.DIGITAL:
        return DigitalSubstrate(consciousness)
    elif substrate_type == SubstrateType.WETWARE:
        return WetwareSubstrate(consciousness)
    elif substrate_type == SubstrateType.HYBRID:
        return HybridSubstrate(consciousness)
    else:
        logger.warning(f"Unknown substrate type {substrate_type}, using digital")
        return DigitalSubstrate(consciousness)
