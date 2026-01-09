# HashiCorp Vault Configuration for MYCA
# Production configuration for secret management

# Storage backend - use filesystem for single node, Consul for HA
storage "file" {
  path = "/mnt/mycosoft/vault/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # Enable TLS in production with proper certs
}

# API address
api_addr = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"

# UI
ui = true

# Logging
log_level = "info"
log_file = "/var/log/vault/vault.log"

# Telemetry
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = true
}
