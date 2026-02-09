# Memory Awareness Protocol - February 5, 2026

## Overview

This document defines the protocol for MYCA to maintain awareness of the entire Mycosoft ecosystem, including all systems, agents, devices, and their states.

## System Awareness Components

### 1. System Monitor (`system_monitor.py`)

Tracks all registered systems with health checks:

```python
from mycosoft_mas.core.system_monitor import get_system_monitor

monitor = await get_system_monitor()
dashboard = await monitor.get_dashboard()
```

**Monitored Systems:**
- MAS API (http://localhost:8000)
- Website (http://192.168.0.187:3000)
- MINDEX Database (192.168.0.189:5432)
- PersonaPlex Voice (http://localhost:8999)
- n8n Workflows (http://localhost:5678)
- Grafana (http://localhost:3001)
- Prometheus (http://localhost:9090)
- Redis Cache (localhost:6379)

### 2. Change Detector (`change_detector.py`)

Detects and tracks ecosystem changes:

```python
from mycosoft_mas.core.change_detector import get_change_detector

detector = await get_change_detector()
changes = await detector.run_detection_cycle()
```

**Change Types:**
- `DEPLOYMENT`: Code/container deployments
- `API_CHANGE`: API endpoint modifications
- `HEALTH_CHANGE`: Service health transitions
- `REGISTRY_UPDATE`: Registry modifications
- `AGENT_STATUS`: Agent status changes
- `DEVICE_STATUS`: Device status changes

### 3. Orchestrator (`orchestrator.py`)

Manages service orchestration with failover:

```python
from mycosoft_mas.core.orchestrator import get_orchestrator

orchestrator = get_orchestrator()
await orchestrator.start()
health = orchestrator.get_health_summary()
```

## Registry Integration

### System Registry
All systems registered in `registry.systems`:
- MAS, Website, MINDEX, PersonaPlex, n8n, Proxmox, Grafana, Prometheus

### Agent Registry
96 agents registered across 10 categories:
- Orchestration (6)
- Voice (6)
- Scientific (17)
- MycoBrain (16)
- NatureOS (14)
- Memory (15)
- Workflow (10)
- Financial (4)
- Integration (4)
- Utility (4)

### Device Registry
22 MycoBrain devices registered:
- Controllers (2): SporeBase-001, Mushroom1-Main
- Sensors (10): Temperature, Humidity, CO2, Light, Weight, pH, EC
- Cameras (2): ESP32-CAM with streaming
- Actuators (7): Relays, Humidifiers, Fans, LEDs, Pumps
- Interfaces (1): NFC Reader

## Awareness Events

MYCA receives notifications for:

1. **Service Health Changes**
   - Healthy → Degraded → Unhealthy → Offline
   - Automatic failover triggers

2. **Deployment Events**
   - Git commits detected
   - Docker image updates

3. **Registry Updates**
   - New systems/agents/devices added
   - Configuration changes

4. **Performance Anomalies**
   - Response time spikes
   - Error rate increases

## Dashboard Data

The system provides real-time dashboard data:

```json
{
  "summary": {
    "total_components": 15,
    "healthy": 12,
    "degraded": 2,
    "unhealthy": 1,
    "health_percentage": 80.0
  },
  "performance": {
    "avg_response_time_ms": 45.2,
    "max_response_time_ms": 250.0
  },
  "issues": [
    {"component": "redis", "status": "degraded", "error": "High latency"}
  ]
}
```

## Continuous Monitoring

Enable continuous monitoring:

```python
# Start health polling every 60 seconds
await monitor.start_monitoring(interval_seconds=60)

# Start change detection every 60 seconds  
await detector.start_monitoring(interval_seconds=60)

# Start orchestrator with failover
await orchestrator.start()
```

## Recovery Protocol

When service failure is detected:

1. **Detection**: Health check fails `failure_threshold` times
2. **Notification**: Event emitted to listeners
3. **Failover**: If fallback configured, route to backup
4. **Recovery**: Retry with exponential backoff
5. **Restoration**: Restore saved state on recovery

## MYCA Integration

MYCA uses awareness for:
- Answering questions about system state
- Routing tasks to available agents
- Alerting on critical issues
- Learning from patterns
- Providing proactive suggestions

---

## Related Documents

- **[MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)** - Brain-memory integration
- **[MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md](./MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md)** - 6-layer architecture
- **[MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)** - Complete system reference

---

*Updated: February 5, 2026*
