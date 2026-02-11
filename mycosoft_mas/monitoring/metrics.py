"""
Metrics Module - February 6, 2026

Prometheus metrics for monitoring.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """A single metric value."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """
    Simple metrics registry for Prometheus-style metrics.
    """
    
    def __init__(self):
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._labels: Dict[str, Dict[str, str]] = {}
    
    def inc(self, name: str, value: float = 1, labels: Optional[Dict] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self.counters[key] += value
        if labels:
            self._labels[key] = labels
    
    def set(self, name: str, value: float, labels: Optional[Dict] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        if labels:
            self._labels[key] = labels
    
    def observe(self, name: str, value: float, labels: Optional[Dict] = None) -> None:
        """Observe a histogram value."""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        
        # Keep only last 1000 observations
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        
        if labels:
            self._labels[key] = labels
    
    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_counter(self, name: str, labels: Optional[Dict] = None) -> float:
        key = self._make_key(name, labels)
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Dict] = None) -> Optional[float]:
        key = self._make_key(name, labels)
        return self.gauges.get(key)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict[str, float]:
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        
        sorted_vals = sorted(values)
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "p50": sorted_vals[len(values) // 2],
            "p95": sorted_vals[int(len(values) * 0.95)] if len(values) >= 20 else sorted_vals[-1],
            "p99": sorted_vals[int(len(values) * 0.99)] if len(values) >= 100 else sorted_vals[-1],
        }
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Counters
        for key, value in self.counters.items():
            lines.append(f"{key} {value}")
        
        # Gauges
        for key, value in self.gauges.items():
            lines.append(f"{key} {value}")
        
        # Histograms (as summary)
        for key, values in self.histograms.items():
            if not values:
                continue
            
            stats = self.get_histogram_stats(key.split("{")[0])
            base_name = key.split("{")[0]
            labels = key[len(base_name):] if "{" in key else ""
            
            lines.append(f"{base_name}_count{labels} {stats['count']}")
            lines.append(f"{base_name}_sum{labels} {stats['sum']}")
        
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {k: self.get_histogram_stats(k.split("{")[0]) for k in self.histograms},
        }


# Backwards-compatible alias (older code/tests expect MetricsCollector)
MetricsCollector = MetricsRegistry


# Global registry
_registry: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


# Common metrics
def record_request(endpoint: str, method: str, status: int, duration_ms: float) -> None:
    """Record an HTTP request."""
    metrics = get_metrics()
    labels = {"endpoint": endpoint, "method": method, "status": str(status)}
    
    metrics.inc("http_requests_total", labels=labels)
    metrics.observe("http_request_duration_ms", duration_ms, labels={"endpoint": endpoint})


def record_collector_fetch(collector: str, events: int, duration_ms: float, success: bool) -> None:
    """Record a collector fetch."""
    metrics = get_metrics()
    
    metrics.inc("collector_fetches_total", labels={"collector": collector, "success": str(success)})
    metrics.inc("collector_events_total", events, labels={"collector": collector})
    metrics.observe("collector_fetch_duration_ms", duration_ms, labels={"collector": collector})


def record_websocket_connection(action: str) -> None:
    """Record WebSocket connection change."""
    metrics = get_metrics()
    metrics.inc(f"websocket_{action}_total")


def update_cache_stats(hit: bool, cache_type: str) -> None:
    """Update cache hit/miss stats."""
    metrics = get_metrics()
    label = "hit" if hit else "miss"
    metrics.inc(f"cache_{label}_total", labels={"type": cache_type})