import pytest
from datetime import datetime
from mycosoft_mas.monitoring.metrics import MetricsCollector, Metric

@pytest.fixture
def metrics_collector():
    collector = MetricsCollector()
    yield collector
    collector.clear_metrics()

def test_service_metrics(metrics_collector):
    # Test service metric recording
    metrics_collector.record_service_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "service_test_metric" in metrics
    assert metrics["service_test_metric"]["value"] == 42.0
    assert metrics["service_test_metric"]["labels"] == {"label": "test"}

def test_agent_metrics(metrics_collector):
    # Test agent metric recording
    metrics_collector.record_agent_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "agent_test_metric" in metrics
    assert metrics["agent_test_metric"]["value"] == 42.0
    assert metrics["agent_test_metric"]["labels"] == {"label": "test"}

def test_security_metrics(metrics_collector):
    # Test security metric recording
    metrics_collector.record_security_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "security_test_metric" in metrics
    assert metrics["security_test_metric"]["value"] == 42.0
    assert metrics["security_test_metric"]["labels"] == {"label": "test"}

def test_evolution_metrics(metrics_collector):
    # Test evolution metric recording
    metrics_collector.record_evolution_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "evolution_test_metric" in metrics
    assert metrics["evolution_test_metric"]["value"] == 42.0
    assert metrics["evolution_test_metric"]["labels"] == {"label": "test"}

def test_integration_metrics(metrics_collector):
    # Test integration metric recording
    metrics_collector.record_integration_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "integration_test_metric" in metrics
    assert metrics["integration_test_metric"]["value"] == 42.0
    assert metrics["integration_test_metric"]["labels"] == {"label": "test"}

def test_dependency_metrics(metrics_collector):
    # Test dependency metric recording
    metrics_collector.record_dependency_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "dependency_test_metric" in metrics
    assert metrics["dependency_test_metric"]["value"] == 42.0
    assert metrics["dependency_test_metric"]["labels"] == {"label": "test"}

def test_resource_metrics(metrics_collector):
    # Test resource metric recording
    metrics_collector.record_resource_metric("test_metric", 42.0, {"label": "test"})
    metrics = metrics_collector.get_metrics()
    assert "resource_test_metric" in metrics
    assert metrics["resource_test_metric"]["value"] == 42.0
    assert metrics["resource_test_metric"]["labels"] == {"label": "test"}

def test_clear_metrics(metrics_collector):
    # Test clearing metrics
    metrics_collector.record_service_metric("test_metric", 42.0)
    metrics_collector.clear_metrics()
    metrics = metrics_collector.get_metrics()
    assert len(metrics) == 0

def test_prometheus_metrics(metrics_collector):
    # Test Prometheus metrics format
    metrics_collector.service_uptime.set(100.0)
    metrics_collector.service_requests.inc()
    metrics_collector.agent_count.set(5)
    metrics_collector.security_alerts.inc()
    
    prom_metrics = metrics_collector.get_prometheus_metrics()
    assert "service_uptime_seconds 100.0" in prom_metrics
    assert "service_requests_total 1.0" in prom_metrics
    assert "agent_count 5.0" in prom_metrics
    assert "security_alerts_total 1.0" in prom_metrics

def test_metric_timestamp(metrics_collector):
    # Test metric timestamp
    metrics_collector.record_service_metric("test_metric", 42.0)
    metrics = metrics_collector.get_metrics()
    timestamp = datetime.fromisoformat(metrics["service_test_metric"]["timestamp"])
    assert isinstance(timestamp, datetime)
    assert (datetime.now() - timestamp).total_seconds() < 1

def test_metric_error_handling(metrics_collector):
    # Test error handling for invalid metrics
    metrics_collector.record_service_metric("test_metric", "invalid")  # Should not raise
    metrics = metrics_collector.get_metrics()
    assert "service_test_metric" not in metrics

def test_concurrent_metrics(metrics_collector):
    # Test concurrent metric recording
    import threading
    
    def record_metrics():
        for i in range(100):
            metrics_collector.record_service_metric(f"metric_{i}", float(i))
    
    threads = [threading.Thread(target=record_metrics) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    metrics = metrics_collector.get_metrics()
    assert len(metrics) == 1000  # 100 metrics * 10 threads

def test_metric_labels(metrics_collector):
    # Test metric labels
    labels = {
        "service": "test_service",
        "environment": "test",
        "version": "1.0.0"
    }
    metrics_collector.record_service_metric("test_metric", 42.0, labels)
    metrics = metrics_collector.get_metrics()
    assert metrics["service_test_metric"]["labels"] == labels

def test_metric_value_types(metrics_collector):
    # Test different metric value types
    metrics_collector.record_service_metric("int_metric", 42)
    metrics_collector.record_service_metric("float_metric", 42.0)
    metrics = metrics_collector.get_metrics()
    assert metrics["service_int_metric"]["value"] == 42.0
    assert metrics["service_float_metric"]["value"] == 42.0

def test_metric_name_sanitization(metrics_collector):
    # Test metric name sanitization
    metrics_collector.record_service_metric("test/metric", 42.0)
    metrics_collector.record_service_metric("test.metric", 42.0)
    metrics = metrics_collector.get_metrics()
    assert "service_test_metric" in metrics
    assert len(metrics) == 1  # Both should map to same sanitized name 