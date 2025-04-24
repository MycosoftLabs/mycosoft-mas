from typing import Dict, List, Any, Callable
from statistics import mean
from datetime import datetime
from mycosoft_mas.services.monitoring_interface import AgentMonitorable

class MonitoringService:
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.health_checks: Dict[str, Callable] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        self.security_metrics: Dict[str, Dict[str, Any]] = {}
        
    def add_health_check(self, name: str, check_func: Callable) -> None:
        """Add a health check function."""
        self.health_checks[name] = check_func
        
    def remove_health_check(self, name: str) -> None:
        """Remove a health check function."""
        self.health_checks.pop(name, None)
        
    def run_health_checks(self) -> Dict[str, bool]:
        """Run all registered health checks."""
        results = {}
        for name, check in self.health_checks.items():
            results[name] = check()
        return results
        
    def add_metric(self, name: str, value: Any) -> None:
        """Add a new metric."""
        self.metrics[name] = value
        
    def update_metric(self, name: str, value: Any) -> None:
        """Update an existing metric."""
        self.metrics[name] = value
        
    def get_metric(self, name: str) -> Any:
        """Get a metric by name."""
        return self.metrics.get(name)
        
    def add_alert(self, alert_id: str, message: str, alert_type: str) -> None:
        """Add a new alert."""
        self.alerts.append({
            'id': alert_id,
            'message': message,
            'type': alert_type,
            'timestamp': datetime.now().isoformat()
        })
        
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        
    def track_performance(self, operation: str, duration: float) -> None:
        """Track performance metrics for an operation."""
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = []
        self.performance_metrics[operation].append(duration)
        
    def get_performance_stats(self, operation: str) -> Dict[str, float]:
        """Get performance statistics for an operation."""
        if operation not in self.performance_metrics:
            return {}
            
        durations = self.performance_metrics[operation]
        return {
            'min': min(durations),
            'max': max(durations),
            'mean': mean(durations),
            'count': len(durations)
        }
        
    def monitor_agent(self, agent: AgentMonitorable) -> None:
        """Monitor an agent that implements the AgentMonitorable interface."""
        metrics = agent.get_metrics()
        status = agent.get_status()
        health = agent.health_check()
        
        self.update_metric(f"{agent.__class__.__name__}_health", health)
        self.update_metric(f"{agent.__class__.__name__}_status", status)
        self.update_metric(f"{agent.__class__.__name__}_metrics", metrics)
        
    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from collected metrics."""
        return {
            'metrics': self.metrics,
            'alerts': self.alerts,
            'performance': {
                op: self.get_performance_stats(op)
                for op in self.performance_metrics
            }
        } 