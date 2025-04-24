from typing import Dict, Any, Callable, Protocol, runtime_checkable

@runtime_checkable
class AgentMonitorable(Protocol):
    """Interface for objects that can be monitored by the MonitoringService."""
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metrics of the object."""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the object."""
        ...
    
    def health_check(self) -> bool:
        """Perform a health check on the object."""
        ... 