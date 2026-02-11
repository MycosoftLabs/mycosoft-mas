from typing import Dict, Any, List
import logging
from datetime import datetime
from mycosoft_mas.monitoring.prometheus_utils import (
    get_counter,
    get_gauge,
    get_histogram,
    get_summary,
)

# Dependency Metrics
dependency_conflicts = get_counter(
    "dependency_conflicts_total",
    "Total number of dependency conflicts",
    labelnames=["service", "conflict_type"],
)
dependency_resolution_time = get_histogram(
    "dependency_resolution_time_seconds",
    "Time taken to resolve dependency conflicts",
    labelnames=["service"],
)

# Integration Metrics
integration_failures = get_counter(
    "integration_failures_total",
    "Total number of integration failures",
    labelnames=["service", "integration_type"],
)
integration_latency = get_histogram(
    "integration_latency_seconds",
    "Integration operation latency",
    labelnames=["service", "operation"],
)

# Task Metrics
task_execution_time = get_histogram(
    "task_execution_time_seconds",
    "Task execution time",
    labelnames=["service", "task_type"],
)
task_success_rate = get_gauge("task_success_rate", "Task success rate", labelnames=["service"])
task_queue_length = get_gauge("task_queue_length", "Number of tasks in queue", labelnames=["service"])

# Security Metrics
security_vulnerability_severity = get_gauge(
    "security_vulnerability_severity",
    "Security vulnerability severity level",
    labelnames=["service", "vulnerability_id"],
)
security_scan_duration = get_histogram(
    "security_scan_duration_seconds",
    "Duration of security scans",
    labelnames=["service"],
)
security_patch_time = get_histogram(
    "security_patch_time_seconds",
    "Time taken to apply security patches",
    labelnames=["service"],
)

# Technology Metrics
technology_update_impact = get_gauge(
    "technology_update_impact_score",
    "Impact score of technology updates",
    labelnames=["service", "update_type"],
)
technology_compatibility = get_gauge(
    "technology_compatibility_score",
    "Technology compatibility score",
    labelnames=["service", "technology"],
)
technology_adoption_rate = get_gauge("technology_adoption_rate", "Rate of technology adoption", labelnames=["service"])

class MetricsCollector:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f'metrics.{service_name}')

    def record_dependency_conflict(self, conflict_type: str, resolution_time: float = None):
        """Record a dependency conflict and its resolution time."""
        dependency_conflicts.labels(service=self.service_name, conflict_type=conflict_type).inc()
        if resolution_time is not None:
            dependency_resolution_time.labels(service=self.service_name).observe(resolution_time)

    def record_integration_failure(self, integration_type: str, latency: float = None):
        """Record an integration failure and its latency."""
        integration_failures.labels(service=self.service_name, integration_type=integration_type).inc()
        if latency is not None:
            integration_latency.labels(service=self.service_name, operation=integration_type).observe(latency)

    def record_task_execution(self, task_type: str, duration: float, success: bool):
        """Record task execution metrics."""
        task_execution_time.labels(service=self.service_name, task_type=task_type).observe(duration)
        
        # Update success rate
        current_rate = task_success_rate.labels(service=self.service_name).get()
        new_rate = (current_rate + (1 if success else 0)) / 2
        task_success_rate.labels(service=self.service_name).set(new_rate)

    def update_task_queue(self, queue_length: int):
        """Update the task queue length metric."""
        task_queue_length.labels(service=self.service_name).set(queue_length)

    def record_security_vulnerability(self, vulnerability_id: str, severity: int, scan_duration: float = None):
        """Record security vulnerability metrics."""
        security_vulnerability_severity.labels(
            service=self.service_name,
            vulnerability_id=vulnerability_id
        ).set(severity)
        
        if scan_duration is not None:
            security_scan_duration.labels(service=self.service_name).observe(scan_duration)

    def record_security_patch(self, duration: float):
        """Record security patch application time."""
        security_patch_time.labels(service=self.service_name).observe(duration)

    def record_technology_update(self, update_type: str, impact_score: float, compatibility_score: float = None):
        """Record technology update metrics."""
        technology_update_impact.labels(
            service=self.service_name,
            update_type=update_type
        ).set(impact_score)
        
        if compatibility_score is not None:
            technology_compatibility.labels(
                service=self.service_name,
                technology=update_type
            ).set(compatibility_score)

    def update_technology_adoption(self, adoption_rate: float):
        """Update technology adoption rate metric."""
        technology_adoption_rate.labels(service=self.service_name).set(adoption_rate)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        return {
            'timestamp': datetime.now().isoformat(),
            'service': self.service_name,
            'metrics': {
                'dependency_conflicts': dependency_conflicts.labels(service=self.service_name)._value.get(),
                'integration_failures': integration_failures.labels(service=self.service_name)._value.get(),
                'task_success_rate': task_success_rate.labels(service=self.service_name)._value.get(),
                'task_queue_length': task_queue_length.labels(service=self.service_name)._value.get(),
                'technology_adoption_rate': technology_adoption_rate.labels(service=self.service_name)._value.get()
            }
        } 