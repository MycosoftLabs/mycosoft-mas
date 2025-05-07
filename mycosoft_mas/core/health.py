from typing import Dict, Any
import logging
from datetime import datetime
import psutil
import redis
import requests
from prometheus_client import Gauge, Counter, Histogram

# Prometheus metrics
service_health = Gauge('service_health', 'Service health status (1=healthy, 0=unhealthy)', ['service'])
service_uptime = Gauge('service_uptime_seconds', 'Service uptime in seconds', ['service'])
service_memory_usage = Gauge('service_memory_usage_bytes', 'Service memory usage in bytes', ['service'])
service_cpu_usage = Gauge('service_cpu_usage_percent', 'Service CPU usage percentage', ['service'])
service_dependencies_health = Gauge('service_dependencies_health', 'Service dependencies health status', ['service', 'dependency'])
service_response_time = Histogram('service_response_time_seconds', 'Service response time in seconds', ['service', 'endpoint'])

class HealthCheck:
    def __init__(self, service_name: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.service_name = service_name
        self.logger = logging.getLogger(f'health.{service_name}')
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.start_time = datetime.now()
        
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check of the service."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': self.service_name,
            'uptime': self._get_uptime(),
            'memory_usage': self._get_memory_usage(),
            'cpu_usage': self._get_cpu_usage(),
            'dependencies': self._check_dependencies(),
            'metrics': self._get_metrics_status()
        }
        
        # Update Prometheus metrics
        service_health.labels(service=self.service_name).set(1 if health_status['status'] == 'healthy' else 0)
        service_uptime.labels(service=self.service_name).set(health_status['uptime'])
        service_memory_usage.labels(service=self.service_name).set(health_status['memory_usage'])
        service_cpu_usage.labels(service=self.service_name).set(health_status['cpu_usage'])
        
        return health_status
    
    def _get_uptime(self) -> float:
        """Calculate service uptime in seconds."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return uptime
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        process = psutil.Process()
        return process.memory_info().rss
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        process = psutil.Process()
        return process.cpu_percent()
    
    def _check_dependencies(self) -> Dict[str, str]:
        """Check health of service dependencies."""
        dependencies = {
            'redis': self._check_redis(),
            'prometheus': self._check_prometheus(),
            'grafana': self._check_grafana()
        }
        
        # Update Prometheus metrics for each dependency
        for dep, status in dependencies.items():
            service_dependencies_health.labels(service=self.service_name, dependency=dep).set(
                1 if status == 'healthy' else 0
            )
        
        return dependencies
    
    def _check_redis(self) -> str:
        """Check Redis connection health."""
        try:
            self.redis_client.ping()
            return 'healthy'
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return 'unhealthy'
    
    def _check_prometheus(self) -> str:
        """Check Prometheus connection health."""
        try:
            response = requests.get('http://prometheus:9090/-/healthy')
            return 'healthy' if response.status_code == 200 else 'unhealthy'
        except Exception as e:
            self.logger.error(f"Prometheus health check failed: {str(e)}")
            return 'unhealthy'
    
    def _check_grafana(self) -> str:
        """Check Grafana connection health."""
        try:
            response = requests.get('http://grafana:3000/api/health')
            return 'healthy' if response.status_code == 200 else 'unhealthy'
        except Exception as e:
            self.logger.error(f"Grafana health check failed: {str(e)}")
            return 'unhealthy'
    
    def _get_metrics_status(self) -> Dict[str, Any]:
        """Get status of service metrics collection."""
        return {
            'metrics_collected': True,
            'last_collection': datetime.now().isoformat(),
            'collection_interval': 15  # seconds
        }
    
    def record_response_time(self, endpoint: str, duration: float):
        """Record response time for a specific endpoint."""
        service_response_time.labels(service=self.service_name, endpoint=endpoint).observe(duration) 