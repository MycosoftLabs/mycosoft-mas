# Mycosoft MAS Dependency Tree

This document provides a comprehensive dependency tree for the Mycosoft Multi-Agent System, organized by category and deployment target (local development vs. server deployment).

## Table of Contents

1. [Core System Dependencies](#core-system-dependencies)
2. [Database & Caching](#database--caching)
3. [Cloud Platform Integrations](#cloud-platform-integrations)
4. [Python Packages](#python-packages)
5. [Node.js Packages](#nodejs-packages)
6. [Monitoring & Observability](#monitoring--observability)
7. [Workflow Automation](#workflow-automation)
8. [Network Management](#network-management)
9. [Development Tools](#development-tools)
10. [Server Deployment Dependencies](#server-deployment-dependencies)

---

## Core System Dependencies

### Required for Local Development

| Dependency | Version | Installation Method | Purpose |
|------------|---------|-------------------|---------|
| **Python** | 3.11+ | Chocolatey: `choco install python311` | Core runtime for MAS |
| **pip** | Latest | Included with Python | Python package manager |
| **Poetry** | Latest | `pip install poetry` or installer script | Python dependency management |
| **Node.js** | LTS (18+) | Chocolatey: `choco install nodejs-lts` | Next.js frontend runtime |
| **npm** | Latest | Included with Node.js | Node.js package manager |
| **Docker Desktop** | Latest | Chocolatey: `choco install docker-desktop` | Container runtime |
| **Git** | Latest | Chocolatey: `choco install git` | Version control |

### Server Deployment

- Same as local, but Docker Desktop replaced with Docker Engine
- Python 3.11+ via system package manager or pyenv
- Node.js LTS via NodeSource repository

---

## Database & Caching

### Local Development

| Dependency | Version | Installation Method | Purpose |
|------------|---------|-------------------|---------|
| **PostgreSQL** | 16+ | Chocolatey: `choco install postgresql` OR Docker | Primary database (MINDEX) |
| **Redis** | 7+ | Chocolatey: `choco install redis-64` OR Docker | Caching and message queue |
| **Qdrant** | 1.7+ | Docker only | Vector database for embeddings |

### Docker Compose Services

```yaml
postgres:
  image: postgres:16
  ports: ["5433:5432"]  # External port 5433 to avoid conflict

redis:
  image: redis:7-alpine
  ports: ["6379:6379"]

qdrant:
  image: qdrant/qdrant:v1.7.3
  ports: ["6333:6333"]
```

### Server Deployment

- PostgreSQL 16+ (system package or Docker)
- Redis 7+ (system package or Docker)
- Qdrant via Docker

---

## Cloud Platform Integrations

### Azure

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Azure CLI** | `choco install azure-cli` | Command-line interface for Azure |
| **Azure SDK (Python)** | `pip install azure-identity azure-mgmt-resource` | Python SDK for Azure Resource Manager |
| **Azure Storage SDK** | `pip install azure-storage-blob` | Blob storage operations |
| **Azure Key Vault SDK** | `pip install azure-keyvault-secrets` | Secret management |

**Environment Variables:**
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SUBSCRIPTION_ID`

### GitHub

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **GitHub CLI** | `choco install gh` | Command-line interface for GitHub |
| **GitHub API** | Via `httpx`/`requests` | REST API integration |

**Authentication:**
- GitHub CLI: `gh auth login`
- API: Personal Access Token or OAuth

### Vercel

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Vercel CLI** | `npm install -g vercel` | Deployment and management |

**Authentication:**
- `vercel login`

### Notion

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Notion SDK** | `pip install notion-client` | Notion API integration |

**Environment Variables:**
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`

### Google Workspace

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Google API Client** | `pip install google-api-python-client` | Google Workspace APIs |
| **Google Auth Libraries** | `pip install google-auth-httplib2 google-auth-oauthlib` | Authentication |

**Setup Required:**
1. Create Google Cloud Project
2. Enable required APIs (Gmail, Drive, Calendar, etc.)
3. Create OAuth 2.0 credentials
4. Download credentials JSON

**Environment Variables:**
- `GOOGLE_APPLICATION_CREDENTIALS` (path to credentials JSON)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

### Asana

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Asana SDK** | `pip install asana` | Asana API integration |

**Environment Variables:**
- `ASANA_ACCESS_TOKEN`
- `ASANA_WORKSPACE_ID`

---

## Python Packages

### Core Framework

```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
```

### Database & ORM

```
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.23
alembic>=1.11.1
redis>=5.0.1
qdrant-client>=1.7.0
```

### HTTP Clients

```
httpx>=0.23.3
aiohttp>=3.9.3
requests>=2.31.0
```

### Monitoring

```
prometheus-client>=0.19.0
```

### Integration SDKs

```
notion-client>=2.2.1
asana>=1.0.0
google-api-python-client>=2.100.0
google-auth-httplib2>=0.1.1
google-auth-oauthlib>=1.1.0
azure-identity>=1.15.0
azure-mgmt-resource>=23.0.0
azure-mgmt-compute>=29.0.0
azure-mgmt-storage>=21.0.0
azure-storage-blob>=12.19.0
azure-keyvault-secrets>=4.7.0
```

### Development Tools

```
pytest>=8.0.0
black>=24.1.1
isort>=5.13.2
mypy>=1.8.0
pylint>=3.0.3
```

### Full Installation

```bash
# Using Poetry (recommended)
poetry install

# Using pip
pip install -r requirements.txt
```

---

## Node.js Packages

### Core Framework

```json
{
  "next": "14.1.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0"
}
```

### UI Components

```json
{
  "@radix-ui/react-*": "^1.0.0 - ^2.0.0",
  "lucide-react": "^0.338.0",
  "tailwindcss": "^3.4.1"
}
```

### State Management

```json
{
  "@tanstack/react-query": "^5.24.1",
  "zustand": "^4.5.1"
}
```

### 3D Visualization

```json
{
  "@react-three/fiber": "^8.15.16",
  "@react-three/drei": "^9.99.4",
  "three": "^0.161.0"
}
```

### Full Installation

```bash
npm install
```

---

## Monitoring & Observability

### Prometheus

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Prometheus** | Docker: `prom/prometheus:v2.52.0` | Metrics collection |
| **Prometheus Client** | `pip install prometheus-client` | Python metrics exporter |

**Configuration:**
- `prometheus/prometheus.yml` - Prometheus configuration
- `prometheus/rules/alerts.yml` - Alert rules

### Grafana

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Grafana** | Docker: `grafana/grafana:10.3.3` | Visualization and dashboards |

**Access:**
- URL: http://localhost:3000
- Default credentials: admin/admin (change on first login)

### Alertmanager

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **Alertmanager** | Docker: `prom/alertmanager:latest` | Alert routing and notifications |

**Configuration:**
- `alertmanager.yml` - Alert routing rules

### Docker Compose Setup

```yaml
prometheus:
  image: prom/prometheus:v2.52.0
  ports: ["9090:9090"]
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana:10.3.3
  ports: ["3000:3000"]
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}

alertmanager:
  image: prom/alertmanager:latest
  ports: ["9093:9093"]
```

---

## Workflow Automation

### N8N

| Component | Installation Method | Purpose |
|-----------|-------------------|---------|
| **N8N** | `npm install -g n8n` OR Docker | Workflow automation platform |

**Local Installation:**
```bash
npm install -g n8n
n8n start
```

**Docker Installation:**
```bash
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n
```

**Access:**
- URL: http://localhost:5678

**Environment Variables:**
- `N8N_WEBHOOK_URL` - Webhook endpoint URL
- `N8N_API_KEY` - API authentication key

---

## Network Management

### Proxmox (Server Only)

| Component | Purpose | Notes |
|-----------|---------|-------|
| **Proxmox VE** | Virtualization platform | Server-side only, not required for local dev |

**Installation:**
- Install Proxmox VE on dedicated server
- Access via web UI: https://server-ip:8006

### Ubiquity/Unify (Server Only)

| Component | Purpose | Notes |
|-----------|---------|-------|
| **UniFi Controller** | Network management | Server-side only, not required for local dev |

**Installation:**
- Deploy UniFi Controller on server
- Access via web UI: https://server-ip:8443

**Note:** These are infrastructure-level tools and not required for local development.

---

## Development Tools

### Code Quality

| Tool | Installation | Purpose |
|------|-------------|---------|
| **Black** | `pip install black` | Python code formatter |
| **isort** | `pip install isort` | Import sorting |
| **mypy** | `pip install mypy` | Type checking |
| **pylint** | `pip install pylint` | Linting |

### Testing

| Tool | Installation | Purpose |
|------|-------------|---------|
| **pytest** | `pip install pytest` | Testing framework |
| **pytest-asyncio** | `pip install pytest-asyncio` | Async test support |

### Version Control

| Tool | Installation | Purpose |
|------|-------------|---------|
| **Git** | `choco install git` | Version control |
| **GitHub CLI** | `choco install gh` | GitHub integration |

---

## Server Deployment Dependencies

### Operating System

- **Linux** (Ubuntu 22.04 LTS recommended)
  - Or Debian 11+
  - Or RHEL 8+

### System Packages

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nodejs \
    npm \
    docker.io \
    docker-compose \
    postgresql-16 \
    redis-server \
    git \
    curl \
    wget \
    build-essential
```

### Docker Setup

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Python Environment

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install --no-dev
```

### Node.js Environment

```bash
# Install Node.js LTS
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install project dependencies
npm install --production
```

### Service Management

- **systemd** for service management
- **nginx** or **Caddy** for reverse proxy
- **certbot** for SSL certificates

### Monitoring (Server)

- Prometheus + Grafana (via Docker Compose)
- Log aggregation (Loki, ELK stack, or similar)
- Uptime monitoring (UptimeRobot, Pingdom, etc.)

---

## Environment Variables Checklist

Create a `.env` file with the following variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mas
MINDEX_DATABASE_URL=postgresql://mindex:mindex@localhost:5432/mindex
REDIS_URL=redis://localhost:6379/0

# Azure
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Notion
NOTION_API_KEY=your-notion-api-key
NOTION_DATABASE_ID=your-database-id

# N8N
N8N_WEBHOOK_URL=http://localhost:5678
N8N_API_KEY=your-n8n-api-key

# Google Workspace
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Asana
ASANA_ACCESS_TOKEN=your-asana-token
ASANA_WORKSPACE_ID=your-workspace-id

# NATUREOS
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your-api-key
NATUREOS_TENANT_ID=your-tenant-id

# Website (Vercel)
WEBSITE_API_URL=https://mycosoft.vercel.app/api
WEBSITE_API_KEY=your-api-key

# Monitoring
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

---

## Installation Order

### Local Development

1. **Core System** → Python, Node.js, Docker, Git
2. **Package Managers** → pip, npm, Poetry
3. **Database & Caching** → PostgreSQL, Redis (or Docker)
4. **Cloud CLIs** → Azure CLI, GitHub CLI, Vercel CLI
5. **Python Packages** → `poetry install` or `pip install -r requirements.txt`
6. **Node.js Packages** → `npm install`
7. **Monitoring** → Docker Compose services
8. **Workflow Automation** → N8N (npm or Docker)
9. **Configuration** → Set up `.env` file with API keys

### Server Deployment

1. **Operating System** → Ubuntu 22.04 LTS
2. **System Packages** → Python, Node.js, Docker, PostgreSQL, Redis
3. **Docker Setup** → Docker Engine + Docker Compose
4. **Application Code** → Clone repository
5. **Python Environment** → Poetry + dependencies
6. **Node.js Environment** → npm + dependencies
7. **Database Setup** → Initialize PostgreSQL databases
8. **Service Configuration** → systemd services
9. **Reverse Proxy** → nginx/Caddy configuration
10. **SSL Certificates** → certbot/Let's Encrypt
11. **Monitoring** → Prometheus + Grafana
12. **Environment Variables** → Production `.env` file

---

## Quick Installation Script

Run the comprehensive installation script:

```powershell
# Windows (PowerShell as Administrator)
.\install_all_dependencies.ps1

# Or with options
.\install_all_dependencies.ps1 -SkipDocker -SkipMonitoring
```

---

## Verification

After installation, verify all dependencies:

```bash
# Check versions
python --version
pip --version
poetry --version
node --version
npm --version
docker --version
git --version
az --version
gh --version
vercel --version
n8n --version

# Check Python packages
pip list | grep -E "(notion|asana|google|azure|prometheus)"

# Check Docker services
docker-compose ps

# Test connections
python -c "import notion_client; print('Notion SDK OK')"
python -c "import asana; print('Asana SDK OK')"
python -c "from google.oauth2 import service_account; print('Google SDK OK')"
python -c "from azure.identity import DefaultAzureCredential; print('Azure SDK OK')"
```

---

## Troubleshooting

### Common Issues

1. **Python version mismatch**
   - Ensure Python 3.11+ is installed
   - Use `pyenv` or `python3.11` explicitly

2. **Docker not running**
   - Start Docker Desktop (Windows/Mac)
   - Start Docker service (Linux): `sudo systemctl start docker`

3. **Port conflicts**
   - PostgreSQL: Use port 5433 for MAS (5432 for local PostgreSQL)
   - Redis: Default 6379
   - Check with: `netstat -ano | findstr :PORT`

4. **Azure authentication**
   - Run `az login`
   - Verify with `az account show`

5. **GitHub authentication**
   - Run `gh auth login`
   - Verify with `gh auth status`

---

## Maintenance

### Update Dependencies

```bash
# Python (Poetry)
poetry update

# Python (pip)
pip list --outdated
pip install --upgrade PACKAGE_NAME

# Node.js
npm outdated
npm update

# System packages (Chocolatey)
choco upgrade all -y

# Docker images
docker-compose pull
docker-compose up -d
```

### Backup Dependencies

```bash
# Python
poetry export -f requirements.txt --output requirements-lock.txt

# Node.js
npm list --depth=0 > npm-dependencies.txt
```

---

## Support

For issues or questions:
- Check project documentation: `docs/`
- Review integration guides: `INTEGRATION_SETUP_GUIDE.md`
- Check system diagnostics: `SYSTEM_DIAGNOSTICS_REPORT.md`
