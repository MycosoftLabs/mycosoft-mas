"""
Mycosoft MAS - Metrics Collection System

This module provides comprehensive metrics collection and monitoring capabilities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from prometheus_client import Counter, Gauge, Histogram, Summary

# Initialize logging
logger = logging.getLogger(__name__)

@dataclass
class Metric:
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime

class MetricsCollector:
    """Collects and manages system metrics."""
    
    def __init__(self):
        # Service metrics
        self.service_health = Gauge(
            'mas_service_health',
            'Health status of MAS services',
            ['service_name']
        )
        
        # Agent metrics
        self.agent_count = Gauge(
            'mas_agent_count',
            'Number of active agents',
            ['cluster_id']
        )
        self.agent_activity = Counter(
            'mas_agent_activity_total',
            'Total agent activities',
            ['agent_id', 'activity_type']
        )
        self.agent_latency = Histogram(
            'mas_agent_latency_seconds',
            'Agent operation latency',
            ['agent_id', 'operation']
        )
        
        # Cluster metrics
        self.cluster_size = Gauge(
            'mas_cluster_size',
            'Number of agents in cluster',
            ['cluster_id']
        )
        self.cluster_health = Gauge(
            'mas_cluster_health',
            'Health status of clusters',
            ['cluster_id']
        )
        
        # Service metrics
        self.service_requests = Counter(
            'mas_service_requests_total',
            'Total service requests',
            ['service_name', 'endpoint']
        )
        self.service_errors = Counter(
            'mas_service_errors_total',
            'Total service errors',
            ['service_name', 'error_type']
        )
        self.service_latency = Histogram(
            'mas_service_latency_seconds',
            'Service operation latency',
            ['service_name', 'operation']
        )
        
        # Resource metrics
        self.resource_usage = Gauge(
            'mas_resource_usage',
            'Resource usage metrics',
            ['resource_type', 'metric']
        )
        self.resource_health = Gauge(
            'mas_resource_health',
            'Health status of resources',
            ['resource_type']
        )
        
        # Evolution metrics
        self.technology_updates = Counter(
            'mas_technology_updates_total',
            'Total technology updates',
            ['technology_type']
        )
        self.evolution_alerts = Counter(
            'mas_evolution_alerts_total',
            'Total evolution alerts',
            ['alert_type']
        )
        
        # Security metrics
        self.security_alerts = Counter(
            'mas_security_alerts_total',
            'Total security alerts',
            ['alert_type', 'severity']
        )
        self.vulnerabilities = Gauge(
            'mas_vulnerabilities',
            'Number of active vulnerabilities',
            ['severity']
        )
        
        # Integration metrics
        self.integration_requests = Counter(
            'mas_integration_requests_total',
            'Total integration requests',
            ['integration_type']
        )
        self.integration_errors = Counter(
            'mas_integration_errors_total',
            'Total integration errors',
            ['integration_type', 'error_type']
        )
        
        # Dependency metrics
        self.dependency_conflicts = Gauge(
            'mas_dependency_conflicts',
            'Number of dependency conflicts',
            ['agent_id']
        )
        self.dependency_updates = Counter(
            'mas_dependency_updates_total',
            'Total dependency updates',
            ['update_type']
        )
        
        # Custom metrics storage
        self._custom_metrics: Dict[str, Metric] = {}

    def record_service_health(self, service_name: str, is_healthy: bool) -> None:
        """Record service health status."""
        self.service_health.labels(service_name=service_name).set(1 if is_healthy else 0)
        
    def record_agent_registration(self, agent_id: str) -> None:
        """Record agent registration."""
        self.agent_activity.labels(agent_id=agent_id, activity_type='registration').inc()
        
    def record_agent_activity(self, agent_id: str, activity_type: str) -> None:
        """Record agent activity."""
        self.agent_activity.labels(agent_id=agent_id, activity_type=activity_type).inc()
        
    def record_agent_latency(self, agent_id: str, operation: str, latency: float) -> None:
        """Record agent operation latency."""
        self.agent_latency.labels(agent_id=agent_id, operation=operation).observe(latency)
        
    def record_cluster_size(self, cluster_id: str, size: int) -> None:
        """Record cluster size."""
        self.cluster_size.labels(cluster_id=cluster_id).set(size)
        
    def record_cluster_health(self, cluster_id: str, is_healthy: bool) -> None:
        """Record cluster health status."""
        self.cluster_health.labels(cluster_id=cluster_id).set(1 if is_healthy else 0)
        
    def record_service_request(self, service_name: str, endpoint: str) -> None:
        """Record service request."""
        self.service_requests.labels(service_name=service_name, endpoint=endpoint).inc()
        
    def record_service_error(self, service_name: str, error_type: str) -> None:
        """Record service error."""
        self.service_errors.labels(service_name=service_name, error_type=error_type).inc()
        
    def record_service_latency(self, service_name: str, operation: str, latency: float) -> None:
        """Record service operation latency."""
        self.service_latency.labels(service_name=service_name, operation=operation).observe(latency)
        
    def record_resource_usage(self, resource_type: str, metric: str, value: float) -> None:
        """Record resource usage."""
        self.resource_usage.labels(resource_type=resource_type, metric=metric).set(value)
        
    def record_resource_health(self, resource_type: str, is_healthy: bool) -> None:
        """Record resource health status."""
        self.resource_health.labels(resource_type=resource_type).set(1 if is_healthy else 0)
        
    def record_technology_update(self, technology_type: str) -> None:
        """Record technology update."""
        self.technology_updates.labels(technology_type=technology_type).inc()
        
    def record_evolution_alert(self, alert_type: str) -> None:
        """Record evolution alert."""
        self.evolution_alerts.labels(alert_type=alert_type).inc()
        
    def record_security_alert(self, alert_type: str, severity: str) -> None:
        """Record security alert."""
        self.security_alerts.labels(alert_type=alert_type, severity=severity).inc()
        
    def record_vulnerability(self, severity: str, count: int) -> None:
        """Record vulnerability count."""
        self.vulnerabilities.labels(severity=severity).set(count)
        
    def record_integration_request(self, integration_type: str) -> None:
        """Record integration request."""
        self.integration_requests.labels(integration_type=integration_type).inc()
        
    def record_integration_error(self, integration_type: str, error_type: str) -> None:
        """Record integration error."""
        self.integration_errors.labels(integration_type=integration_type, error_type=error_type).inc()
        
    def record_dependency_conflict(self, agent_id: str, count: int) -> None:
        """Record dependency conflict count."""
        self.dependency_conflicts.labels(agent_id=agent_id).set(count)
        
    def record_dependency_update(self, update_type: str) -> None:
        """Record dependency update."""
        self.dependency_updates.labels(update_type=update_type).inc()
        
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of metrics collection."""
        return {
            'metrics_collected': True,
            'last_update': datetime.now().isoformat()
        }

    def record_service_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a service-level metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"service_{name}"] = metric
            logger.debug(f"Recorded service metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording service metric: {e}")

    def record_agent_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an agent-level metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"agent_{name}"] = metric
            logger.debug(f"Recorded agent metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording agent metric: {e}")

    def record_security_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a security-related metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"security_{name}"] = metric
            logger.debug(f"Recorded security metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording security metric: {e}")

    def record_evolution_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an evolution-related metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"evolution_{name}"] = metric
            logger.debug(f"Recorded evolution metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording evolution metric: {e}")

    def record_integration_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an integration-related metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"integration_{name}"] = metric
            logger.debug(f"Recorded integration metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording integration metric: {e}")

    def record_dependency_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a dependency-related metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"dependency_{name}"] = metric
            logger.debug(f"Recorded dependency metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording dependency metric: {e}")

    def record_resource_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a resource-related metric."""
        try:
            metric = Metric(name, value, labels or {}, datetime.now())
            self._custom_metrics[f"resource_{name}"] = metric
            logger.debug(f"Recorded resource metric: {name}={value}")
        except Exception as e:
            logger.error(f"Error recording resource metric: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return {
            name: {
                "value": metric.value,
                "labels": metric.labels,
                "timestamp": metric.timestamp.isoformat()
            }
            for name, metric in self._custom_metrics.items()
        }

    def clear_metrics(self):
        """Clear all recorded metrics."""
        self._custom_metrics.clear()
        logger.info("Cleared all metrics")

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        metrics = []
        
        # Service metrics
        metrics.append(f"service_uptime_seconds {self.service_uptime._value.get()}")
        metrics.append(f"service_requests_total {self.service_requests._value.get()}")
        metrics.append(f"service_errors_total {self.service_errors._value.get()}")
        
        # Agent metrics
        metrics.append(f"agent_count {self.agent_count._value.get()}")
        metrics.append(f"agent_messages_total {self.agent_messages._value.get()}")
        metrics.append(f"agent_errors_total {self.agent_errors._value.get()}")
        
        # Security metrics
        metrics.append(f"security_alerts_total {self.security_alerts._value.get()}")
        metrics.append(f"security_vulnerabilities {self.security_vulnerabilities._value.get()}")
        metrics.append(f"security_updates_total {self.security_updates._value.get()}")
        
        # Evolution metrics
        metrics.append(f"technology_updates_total {self.technology_updates._value.get()}")
        metrics.append(f"evolution_alerts_total {self.evolution_alerts._value.get()}")
        metrics.append(f"system_updates_total {self.system_updates._value.get()}")
        
        # Integration metrics
        metrics.append(f"integration_requests_total {self.integration_requests._value.get()}")
        metrics.append(f"integration_errors_total {self.integration_errors._value.get()}")
        
        # Dependency metrics
        metrics.append(f"dependency_count {self.dependency_count._value.get()}")
        metrics.append(f"dependency_updates_total {self.dependency_updates._value.get()}")
        metrics.append(f"dependency_conflicts {self.dependency_conflicts._value.get()}")
        
        # Resource metrics
        metrics.append(f"cpu_usage_percent {self.cpu_usage._value.get()}")
        metrics.append(f"memory_usage_bytes {self.memory_usage._value.get()}")
        metrics.append(f"disk_usage_bytes {self.disk_usage._value.get()}")
        metrics.append(f"network_traffic_bytes {self.network_traffic._value.get()}")
        
        return "\n".join(metrics)
