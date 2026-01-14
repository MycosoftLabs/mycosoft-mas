# Observability Stack Setup Guide

This guide covers the setup and configuration of the Mycosoft MAS observability stack, including Prometheus, Grafana, Loki, and Promtail.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Prometheus  │    │    Grafana    │    │    Loki      │      │
│  │   :9090      │───▶│    :3002      │◀───│   :3101      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ▲                                        ▲              │
│         │                                        │              │
│  ┌──────┴──────────────────────────────┬────────┴─────┐        │
│  │                                     │              │        │
│  │  ┌────────────┐  ┌────────────┐    │  ┌──────────┐│        │
│  │  │  MycoBrain │  │   MINDEX   │    │  │ Promtail ││        │
│  │  │  Devices   │  │   :8000    │    │  │ (sidecar)││        │
│  │  │  /metrics  │  │  /metrics  │    │  └──────────┘│        │
│  │  └────────────┘  └────────────┘    │       │      │        │
│  │         ▲              ▲           │       ▼      │        │
│  │         │              │           │   Log Files  │        │
│  │  ┌──────┴──────────────┴─────┐     │              │        │
│  │  │     MycoBrain Service     │     │              │        │
│  │  │         :8003             │─────┴──────────────┘        │
│  │  └───────────────────────────┘                             │
│  │                                                             │
└──┴─────────────────────────────────────────────────────────────┘
```

## Port Assignments

| Service | Port | Description |
|---------|------|-------------|
| Prometheus | 9090 | Metrics collector and query engine |
| Grafana | 3002 | Dashboards and visualization |
| Loki | 3101 | Log aggregation (moved from 3100) |
| Promtail | - | Log shipper (internal) |

> **Note:** Loki uses port 3101 to avoid conflict with MICA UniFi Dashboard on port 3100.

## Quick Start

### 1. Start the Observability Stack

```bash
# Start Loki and Promtail
docker compose -f docker/observability.yml up -d

# Verify services are running
docker compose -f docker/observability.yml ps
```

### 2. Access Grafana

1. Open http://localhost:3002
2. Default credentials: admin/admin
3. Dashboards are auto-provisioned from `grafana/dashboards/`

### 3. Available Dashboards

- **Fleet Health** (`/d/fleet-health`) - Device status, temperature, humidity, VOC
- **Logs Explorer** (`/d/logs-explorer`) - Live log viewer with Loki

## Configuration Files

### Prometheus (`prometheus.yml`)

The Prometheus configuration includes scrape jobs for:

- `mas-orchestrator` - MAS Orchestrator metrics
- `mas-agent-manager` - Agent manager metrics
- `mycobrain-service` - MycoBrain device management service
- `mycobrain-devices` - Individual device metrics (when enabled)
- `mindex-api` - MINDEX API metrics
- `loki` - Loki health metrics

### Loki (`loki/loki-config.yml`)

- **Retention:** 7 days
- **Storage:** Local filesystem
- **Ingestion rate:** 4 MB/s

### Promtail (`promtail/promtail-config.yml`)

Scrapes logs from:
- MAS application logs (`logs/*.log`)
- MycoBrain device logs
- MINDEX API logs
- Error logs (with label extraction)

## Adding MycoBrain Device Metrics

### Firmware Requirements

MycoBrain devices expose a `/metrics` endpoint in Prometheus format:

```
# HELP myco_temperature_c Temperature in Celsius
# TYPE myco_temperature_c gauge
myco_temperature_c{device_id="myco-001"} 23.5

# HELP myco_humidity_pct Relative humidity percentage
# TYPE myco_humidity_pct gauge
myco_humidity_pct{device_id="myco-001"} 65.0

# HELP myco_voc_index VOC index (0-500)
# TYPE myco_voc_index gauge
myco_voc_index{device_id="myco-001"} 45

# HELP myco_wifi_rssi_dbm WiFi signal strength
# TYPE myco_wifi_rssi_dbm gauge
myco_wifi_rssi_dbm{device_id="myco-001"} -67
```

### Adding Devices to Prometheus

Edit `prometheus.yml` to add device targets:

```yaml
- job_name: 'mycobrain-devices'
  static_configs:
    - targets:
        - '192.168.1.100:80'  # Device 1
        - '192.168.1.101:80'  # Device 2
      labels:
        device_type: 'mycobrain'
```

## Alerting Rules

Alert rules are defined in `prometheus/alerts.yml`:

### Device Alerts
- **DeviceDown** - No metrics for 3 minutes (critical)
- **DeviceDegraded** - Less than 80% uptime in 5 minutes (warning)

### Environmental Alerts
- **HighTemperature** - Temperature > 35°C for 5 minutes
- **LowTemperature** - Temperature < 5°C for 5 minutes
- **VOCSpike** - VOC index > 90 for 2 minutes
- **HumidityOutOfRange** - Humidity <30% or >80% for 10 minutes

### Connectivity Alerts
- **WeakWiFiSignal** - RSSI < -80 dBm for 5 minutes

### Service Alerts
- **MINDEXDown** - MINDEX API not responding (critical)
- **MycoBrainServiceDown** - MycoBrain service not responding (critical)
- **LokiDown** - Loki not responding (warning)

## Querying Logs

### Grafana Explore

1. Go to Grafana → Explore
2. Select Loki data source
3. Use LogQL queries:

```logql
# All logs from MAS
{app="mycosoft-mas"}

# Error logs only
{level="error"}

# Logs containing specific text
{app=~".+"} |= "BME688"

# Logs from MycoBrain service
{job="mycobrain"} | json | line_format "{{.message}}"
```

### Common Queries

```logql
# Count errors per service (last hour)
sum(count_over_time({level="error"}[1h])) by (app)

# Rate of log entries
rate({app=~".+"}[5m])

# Search for device connections
{app="mycobrain-service"} |= "connected"
```

## Azure IoT Hub Integration

For remote devices (LoRaWAN, cellular), use Azure IoT Hub with an Azure Function to bridge telemetry to Prometheus:

1. Deploy Azure Function App (see `infra/azure-function/`)
2. Configure IoT Hub message routing
3. Function pushes metrics to Prometheus Pushgateway

## Troubleshooting

### Loki Not Receiving Logs

1. Check Promtail is running: `docker logs mycosoft-promtail`
2. Verify log paths in `promtail/promtail-config.yml`
3. Ensure log files exist and are readable

### Prometheus Not Scraping

1. Check targets: http://localhost:9090/targets
2. Verify service is exposing `/metrics`
3. Check firewall rules for Docker networking

### Grafana Dashboard Not Loading

1. Check data source configuration
2. Verify Prometheus/Loki are accessible
3. Check browser console for errors

## Extending the Stack

### Adding Custom Metrics

1. Expose `/metrics` endpoint in your service
2. Add scrape job to `prometheus.yml`
3. Create Grafana dashboard or add panels

### Adding Custom Dashboards

1. Create JSON dashboard in Grafana UI
2. Export to `grafana/dashboards/`
3. Dashboard will auto-load on next restart

### Adding Alert Rules

1. Add rules to `prometheus/alerts.yml`
2. Configure Alertmanager for notifications
3. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`

## Security Considerations

- **Production:** Enable authentication on Grafana
- **Network:** Use Docker networks to isolate observability stack
- **TLS:** Enable HTTPS for all services in production
- **RBAC:** Configure Grafana roles for team members
