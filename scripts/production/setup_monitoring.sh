#!/bin/bash
# Setup monitoring stack on myca-api VM
# Prometheus + Grafana + Loki

set -e

echo "=================================================="
echo "  MYCA Monitoring Stack Setup"
echo "=================================================="

NAS_PATH="/mnt/mycosoft"

# Create directories
echo "[1/5] Creating directories..."
mkdir -p $NAS_PATH/monitoring/{prometheus,grafana,loki}
mkdir -p /opt/myca/monitoring

# Create Prometheus config
echo "[2/5] Creating Prometheus configuration..."
cat > /opt/myca/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files: []

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # MYCA API
  - job_name: 'myca-api'
    static_configs:
      - targets: ['myca-api:8001']
    metrics_path: /metrics

  # MINDEX
  - job_name: 'mindex'
    static_configs:
      - targets: ['mindex:8000']

  # Node Exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: 
        - '192.168.20.10:9100'  # API VM
        - '192.168.20.11:9100'  # Website VM
        - '192.168.20.12:9100'  # Database VM

  # Docker containers
  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:9323']

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['192.168.20.12:9187']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['192.168.20.12:9121']
EOF

# Create Loki config
echo "[3/5] Creating Loki configuration..."
cat > /opt/myca/monitoring/loki-config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s
EOF

# Create docker-compose for monitoring
echo "[4/5] Creating docker-compose.monitoring.yml..."
cat > /opt/myca/docker-compose.monitoring.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: myca-prometheus
    restart: always
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - /mnt/mycosoft/monitoring/prometheus:/prometheus
    ports:
      - "9090:9090"
    networks:
      - myca-network
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    container_name: myca-grafana
    restart: always
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.mycosoft.com
    volumes:
      - /mnt/mycosoft/monitoring/grafana:/var/lib/grafana
    ports:
      - "3002:3000"
    networks:
      - myca-network
    depends_on:
      - prometheus

  loki:
    image: grafana/loki:latest
    container_name: myca-loki
    restart: always
    volumes:
      - ./monitoring/loki-config.yml:/etc/loki/local-config.yaml
      - /mnt/mycosoft/monitoring/loki:/loki
    ports:
      - "3100:3100"
    networks:
      - myca-network
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:latest
    container_name: myca-promtail
    restart: always
    volumes:
      - /var/log:/var/log:ro
      - /var/log/myca:/var/log/myca:ro
      - ./monitoring/promtail-config.yml:/etc/promtail/config.yml
    networks:
      - myca-network
    command: -config.file=/etc/promtail/config.yml

  node-exporter:
    image: prom/node-exporter:latest
    container_name: myca-node-exporter
    restart: always
    ports:
      - "9100:9100"
    networks:
      - myca-network
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'

networks:
  myca-network:
    external: true
EOF

# Create Promtail config
cat > /opt/myca/monitoring/promtail-config.yml << 'EOF'
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: myca-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: myca
          __path__: /var/log/myca/*.log

  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: system
          __path__: /var/log/syslog
EOF

# Start monitoring
echo "[5/5] Starting monitoring stack..."
cd /opt/myca
docker compose -f docker-compose.monitoring.yml up -d

echo ""
echo "=================================================="
echo "  Monitoring Stack Deployed!"
echo "=================================================="
echo ""
echo "  Services:"
echo "    Prometheus: http://localhost:9090"
echo "    Grafana: http://localhost:3002 (admin/admin)"
echo "    Loki: http://localhost:3100"
echo ""
echo "  Next steps:"
echo "    1. Access Grafana and change admin password"
echo "    2. Add Prometheus data source: http://prometheus:9090"
echo "    3. Add Loki data source: http://loki:3100"
echo "    4. Import dashboards for Node, Docker, PostgreSQL"
echo ""
