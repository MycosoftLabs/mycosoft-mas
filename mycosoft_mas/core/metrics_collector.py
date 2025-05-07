"""
Metrics Collector for Mycosoft MAS

This module collects and manages system-wide metrics for the MAS platform.
"""

import psutil
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import logging
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
AGENT_COUNT = Gauge('mas_agent_count', 'Number of active agents')
TASK_COUNT = Counter('mas_task_count', 'Total number of tasks processed')
ERROR_COUNT = Counter('mas_error_count', 'Total number of errors')
API_CALLS = Counter('mas_api_calls', 'Total number of API calls')
CPU_USAGE = Gauge('mas_cpu_usage', 'System CPU usage')
MEMORY_USAGE = Gauge('mas_memory_usage', 'System memory usage')
TASK_DURATION = Histogram('mas_task_duration_seconds', 'Task execution duration')

class MetricsCollector:
    """Collects and manages system-wide metrics."""
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.start_time = time.time()
        self.metrics = {
            "agent_count": 0,
            "task_count": 0,
            "error_count": 0,
            "api_calls": 0,
            "cpu_usage": 0,
            "memory_usage": 0,
            "last_update": time.time()
        }
        self.performance_history = {
            "labels": [],
            "cpu": [],
            "memory": []
        }
        self.max_history_points = 100
        
    async def initialize(self):
        """Initialize the metrics collector."""
        logger.info("Initializing metrics collector")
        # Start background metrics collection
        asyncio.create_task(self._collect_metrics())
        
    async def _collect_metrics(self):
        """Continuously collect system metrics."""
        while True:
            try:
                # Update system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                # Update Prometheus metrics
                CPU_USAGE.set(cpu_percent)
                MEMORY_USAGE.set(memory_percent)
                
                # Update internal metrics
                self.metrics["cpu_usage"] = cpu_percent
                self.metrics["memory_usage"] = memory_percent
                self.metrics["last_update"] = time.time()
                
                # Update performance history
                current_time = datetime.now().strftime("%H:%M:%S")
                self.performance_history["labels"].append(current_time)
                self.performance_history["cpu"].append(cpu_percent)
                self.performance_history["memory"].append(memory_percent)
                
                # Keep history within limits
                if len(self.performance_history["labels"]) > self.max_history_points:
                    self.performance_history["labels"].pop(0)
                    self.performance_history["cpu"].pop(0)
                    self.performance_history["memory"].pop(0)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {str(e)}")
                self.increment_error_count()
            
            await asyncio.sleep(15)  # Collect metrics every 15 seconds
    
    def increment_agent_count(self):
        """Increment the active agent count."""
        self.metrics["agent_count"] += 1
        AGENT_COUNT.inc()
    
    def decrement_agent_count(self):
        """Decrement the active agent count."""
        self.metrics["agent_count"] = max(0, self.metrics["agent_count"] - 1)
        AGENT_COUNT.dec()
    
    def increment_task_count(self):
        """Increment the task count."""
        self.metrics["task_count"] += 1
        TASK_COUNT.inc()
    
    def increment_error_count(self):
        """Increment the error count."""
        self.metrics["error_count"] += 1
        ERROR_COUNT.inc()
    
    def increment_api_calls(self):
        """Increment the API call count."""
        self.metrics["api_calls"] += 1
        API_CALLS.inc()
    
    def record_task_duration(self, duration: float):
        """Record a task's execution duration."""
        TASK_DURATION.observe(duration)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            "performance_data": {
                "labels": self.performance_history["labels"],
                "cpu": self.performance_history["cpu"],
                "memory": self.performance_history["memory"]
            },
            "uptime": time.time() - self.start_time
        }
    
    def get_performance_data(self) -> Dict[str, List]:
        """Get performance history data."""
        return self.performance_history
    
    def reset_metrics(self):
        """Reset all metrics to initial values."""
        self.metrics = {
            "agent_count": 0,
            "task_count": 0,
            "error_count": 0,
            "api_calls": 0,
            "cpu_usage": 0,
            "memory_usage": 0,
            "last_update": time.time()
        }
        self.performance_history = {
            "labels": [],
            "cpu": [],
            "memory": []
        }
        logger.info("Metrics reset to initial values") 