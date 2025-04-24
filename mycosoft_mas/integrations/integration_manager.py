from typing import Dict, Any, Callable
from datetime import datetime

class IntegrationManager:
    def __init__(self):
        self.integrations: Dict[str, Callable] = {}  # integration_id -> handler
        self.adapters: Dict[str, Callable] = {}  # adapter_id -> handler
        self.connection_pool: Dict[str, Any] = {}  # connection_id -> connection
        self.integration_metrics: Dict[str, Dict[str, Any]] = {}  # integration_id -> metrics
        
    def register_integration(self, integration_id: str, handler: Callable) -> None:
        """Register a new integration handler."""
        self.integrations[integration_id] = handler
        
    def unregister_integration(self, integration_id: str) -> None:
        """Unregister an integration handler."""
        self.integrations.pop(integration_id, None)
        
    def add_adapter(self, adapter_id: str, handler: Callable) -> None:
        """Add a new data adapter."""
        self.adapters[adapter_id] = handler
        
    def remove_adapter(self, adapter_id: str) -> None:
        """Remove a data adapter."""
        self.adapters.pop(adapter_id, None)
        
    def establish_connection(self, connection_id: str, config: Dict[str, Any]) -> Any:
        """Establish a new connection."""
        # In a real implementation, this would create actual connections
        # For testing purposes, we just store the config
        connection = {
            "id": connection_id,
            "config": config,
            "established_at": datetime.now()
        }
        self.connection_pool[connection_id] = connection
        return connection
        
    def close_connection(self, connection_id: str) -> None:
        """Close a connection."""
        if connection_id in self.connection_pool:
            # In a real implementation, this would properly close the connection
            self.connection_pool.pop(connection_id)
            
    def execute_integration(self, integration_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an integration handler."""
        if integration_id not in self.integrations:
            raise ValueError(f"Integration {integration_id} not found")
            
        handler = self.integrations[integration_id]
        result = handler(data)
        
        # Update metrics
        self.monitor_integration(integration_id)
        
        return result
        
    def transform_data(self, adapter_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data using an adapter."""
        if adapter_id not in self.adapters:
            raise ValueError(f"Adapter {adapter_id} not found")
            
        handler = self.adapters[adapter_id]
        return handler(data)
        
    def monitor_integration(self, integration_id: str) -> None:
        """Monitor integration metrics."""
        if integration_id not in self.integration_metrics:
            self.integration_metrics[integration_id] = {
                "last_execution": None,
                "execution_count": 0,
                "success_count": 0,
                "error_count": 0,
                "average_response_time": 0
            }
            
        metrics = self.integration_metrics[integration_id]
        metrics["last_execution"] = datetime.now()
        metrics["execution_count"] += 1
        
    def get_integration_status(self, integration_id: str) -> Dict[str, Any]:
        """Get the status of an integration."""
        if integration_id not in self.integration_metrics:
            return {
                "is_active": False,
                "last_execution": None,
                "execution_count": 0
            }
            
        metrics = self.integration_metrics[integration_id]
        return {
            "is_active": integration_id in self.integrations,
            "last_execution": metrics["last_execution"],
            "execution_count": metrics["execution_count"]
        }
        
    def generate_integration_report(self) -> Dict[str, Dict[str, Any]]:
        """Generate a comprehensive integration report."""
        report = {}
        for integration_id in self.integration_metrics:
            report[integration_id] = self.get_integration_status(integration_id)
        return report 