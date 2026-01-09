# Monitoring Stack for MYCA

This document describes the Prometheus, Grafana, and Loki monitoring stack for MYCA.

## Overview

| Component | Port | Purpose |
|-----------|------|---------|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Dashboards and visualization |
| Loki | 3100 | Log aggregation |
| Alertmanager | 9093 | Alert routing and notification |
| Node Exporter | 9100 | Host metrics |
| cAdvisor | 8080 | Container metrics |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MYCA Monitoring Stack                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │ MAS      │    │ Postgres │    │ Redis    │                  │
│  │ Exporter │    │ Exporter │    │ Exporter │                  │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                  │
│       │               │               │                         │
│       └───────────────┼───────────────┘                         │
│                       ▼                                          │
│              ┌────────────────┐                                  │
│              │   Prometheus   │◄──── Metrics Storage            │
│              └───────┬────────┘                                  │
│                      │                                           │
│                      ▼                                           │
│              ┌────────────────┐                                  │
│              │    Grafana     │◄──── Dashboards                 │
│              └───────┬────────┘                                  │
│                      │                                           │
│              ┌───────┴───────┐                                   │
│              │ Alertmanager  │──► Morgan (Slack/Email/SMS)      │
│              └───────────────┘                                   │
│                                                                  │
│  ┌──────────┐                 ┌──────────┐                      │
│  │ Promtail │────────────────►│   Loki   │◄──── Log Storage    │
│  │ (agents) │                 └──────────┘                      │
│  └──────────┘                                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment

The monitoring stack is defined in the existing `docker-compose.yml`. Key services:

### Prometheus Configuration

The existing `prometheus.yml` collects metrics from all MYCA services. Update to include:

```yaml
# prometheus.yml additions
scrape_configs:
  - job_name: 'myca-orchestrator'
    static_configs:
      - targets: ['mas-orchestrator:8000']
    metrics_path: /metrics
    
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    
  - job_name: 'vault'
    static_configs:
      - targets: ['vault:8200']
    metrics_path: /v1/sys/metrics
    params:
      format: ['prometheus']
```

### Alertmanager Configuration

Configure alerts for critical MYCA systems:

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@mycosoft.com'
  
route:
  receiver: 'myca-team'
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  
  routes:
    - match:
        severity: critical
      receiver: 'morgan-urgent'
    - match:
        service: myca
      receiver: 'myca-team'

receivers:
  - name: 'myca-team'
    email_configs:
      - to: 'morgan@mycosoft.com'
        
  - name: 'morgan-urgent'
    email_configs:
      - to: 'morgan@mycosoft.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx'
        channel: '#myca-alerts'
```

## Grafana Dashboards

### Pre-built Dashboards

Import these Grafana dashboards:

| Dashboard ID | Name | Purpose |
|--------------|------|---------|
| 1860 | Node Exporter Full | Host metrics |
| 893 | Docker and Container | Container metrics |
| 455 | PostgreSQL Database | Database metrics |
| 763 | Redis | Cache metrics |
| 15798 | Qdrant | Vector DB metrics |

### Custom MYCA Dashboard

Create custom dashboard for MYCA-specific metrics:

1. Agent Status Panel
2. Task Queue Length
3. Voice Pipeline Latency
4. N8N Workflow Executions
5. Knowledge Base Size
6. API Request Rate

## Log Aggregation with Loki

### Promtail Configuration

Deploy Promtail on each VM to ship logs:

```yaml
# promtail-config.yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: myca
    static_configs:
      - targets:
          - localhost
        labels:
          job: myca
          __path__: /var/log/myca/*.log
          
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: container
```

## Alert Rules

### Critical Alerts

```yaml
# prometheus/rules/myca-alerts.yml
groups:
  - name: myca-critical
    rules:
      - alert: MYCADown
        expr: up{job="myca-orchestrator"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MYCA Orchestrator is down"
          
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL database is down"
          
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          
      - alert: NASStorageLow
        expr: (node_filesystem_avail_bytes{mountpoint="/mnt/mycosoft"} / node_filesystem_size_bytes{mountpoint="/mnt/mycosoft"}) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "NAS storage below 10%"
          
      - alert: AgentPoolExhausted
        expr: myca_agent_active_count >= myca_agent_max_parallel
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "All agent slots are occupied"
```

## Installation

Deploy the monitoring stack on MYCA Core VM:

```bash
# Navigate to project directory
cd /opt/myca

# Start monitoring services
docker compose up -d prometheus grafana loki alertmanager promtail

# Verify services
docker compose ps
```

## Access

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://192.168.20.10:3001 | admin / (set on first login) |
| Prometheus | http://192.168.20.10:9090 | (no auth) |
| Alertmanager | http://192.168.20.10:9093 | (no auth) |

## Health Endpoints

Add to MYCA API for monitoring:

```
GET /health          - Overall system health
GET /health/agents   - Agent pool status
GET /health/storage  - NAS storage status
GET /metrics         - Prometheus metrics
```

## Retention Settings

Configure data retention:

```yaml
# Prometheus retention
--storage.tsdb.retention.time=30d
--storage.tsdb.retention.size=50GB

# Loki retention
compactor:
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
  
limits_config:
  retention_period: 30d
```

## Backup

Backup monitoring data to NAS:

```bash
# Prometheus snapshots
curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Grafana dashboards
grafana-cli admin export /mnt/mycosoft/backups/grafana/

# Loki - backed by NAS storage automatically
```
