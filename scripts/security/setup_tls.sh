#!/bin/bash
# setup_tls.sh - TLS/mTLS automation for Mycosoft services
# Created: March 5, 2026
#
# External services: Use Let's Encrypt (Caddy handles this via Caddyfile.prod)
# Internal services: Self-signed certs for service-to-service mTLS
#
# Usage:
#   ./setup_tls.sh external   # Certbot/ACME for public-facing
#   ./setup_tls.sh internal   # Generate self-signed for internal APIs
#
# Env:
#   CERT_DIR     - Output directory (default: /etc/mycosoft/certs)
#   DOMAIN       - Domain for Let's Encrypt (e.g. mycosoft.com)

set -e

CERT_DIR="${CERT_DIR:-/etc/mycosoft/certs}"
DOMAIN="${DOMAIN:-mycosoft.com}"

mkdir -p "${CERT_DIR}"
cd "${CERT_DIR}"

case "${1:-}" in
  internal)
    echo "Generating self-signed certs for internal mTLS..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout internal-key.pem -out internal-cert.pem \
      -subj "/CN=mycosoft-internal/O=Mycosoft"
    chmod 600 internal-key.pem
    echo "Created ${CERT_DIR}/internal-cert.pem and internal-key.pem"
    ;;
  external)
    echo "For external TLS, use Caddy with Caddyfile.prod or certbot:"
    echo "  certbot certonly --standalone -d ${DOMAIN}"
    echo "  # Or use Caddy's automatic HTTPS"
    ;;
  *)
    echo "Usage: $0 {internal|external}"
    echo "  internal - Generate self-signed certs for internal mTLS"
    echo "  external - Show instructions for Let's Encrypt"
    exit 1
    ;;
esac
