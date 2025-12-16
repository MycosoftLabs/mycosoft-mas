# Installation Report - Mycosoft MAS Dependencies

**Date:** Generated on installation  
**System:** Windows 10/11  
**Installation Method:** Automated Scripts + Manual Verification

## Installation Scripts Created

### 1. `install_all_dependencies.ps1`
Comprehensive PowerShell script that installs all system-level dependencies:
- Core tools (Python, Node.js, Docker, Git)
- Database tools (PostgreSQL, Redis)
- Cloud CLIs (Azure CLI, GitHub CLI, Vercel CLI)
- Monitoring tools (Prometheus, Grafana via Docker)
- Workflow automation (N8N)

**Usage:**
```powershell
# Run as Administrator
.\install_all_dependencies.ps1
```

### 2. `install_python_packages.py`
Python script that installs all Python integration packages:
- Notion SDK
- Asana SDK
- Google Workspace SDK
- Azure SDK
- Prometheus client
- Database drivers
- Core framework packages

**Usage:**
```bash
python install_python_packages.py
```

### 3. `install_node_packages.ps1`
PowerShell script for Node.js packages:
- Project dependencies from package.json
- Global tools (Vercel CLI, N8N)

**Usage:**
```powershell
.\install_node_packages.ps1
```

### 4. `check_dependencies.ps1`
Verification script to check installed dependencies.

**Usage:**
```powershell
.\check_dependencies.ps1
```

## Dependency Tree Document

Created `DEPENDENCY_TREE.md` with comprehensive documentation:
- Complete dependency list organized by category
- Installation methods for each dependency
- Environment variable requirements
- Server deployment instructions
- Troubleshooting guide

## Installation Checklist

### Core System Dependencies

- [ ] **Python 3.11+**
  - Install: `choco install python311`
  - Verify: `python --version`

- [ ] **pip**
  - Included with Python
  - Upgrade: `python -m pip install --upgrade pip`

- [ ] **Poetry**
  - Install: `pip install poetry` or use installer script
  - Verify: `poetry --version`

- [ ] **Node.js LTS**
  - Install: `choco install nodejs-lts`
  - Verify: `node --version`

- [ ] **npm**
  - Included with Node.js
  - Verify: `npm --version`

- [ ] **Docker Desktop**
  - Install: `choco install docker-desktop`
  - Verify: `docker --version`
  - Start Docker Desktop application

- [ ] **Git**
  - Install: `choco install git`
  - Verify: `git --version`

### Database & Caching

- [ ] **PostgreSQL** (Optional - can use Docker)
  - Install: `choco install postgresql`
  - OR use Docker: `docker-compose up postgres`
  - Verify: `psql --version`

- [ ] **Redis** (Optional - can use Docker)
  - Install: `choco install redis-64`
  - OR use Docker: `docker-compose up redis`
  - Verify: `redis-cli --version`

- [ ] **Qdrant** (Docker only)
  - Via docker-compose: `docker-compose up qdrant`

### Cloud Platform CLIs

- [ ] **Azure CLI**
  - Install: `choco install azure-cli`
  - Verify: `az --version`
  - Login: `az login`

- [ ] **GitHub CLI**
  - Install: `choco install gh`
  - Verify: `gh --version`
  - Login: `gh auth login`

- [ ] **Vercel CLI**
  - Install: `npm install -g vercel`
  - Verify: `vercel --version`
  - Login: `vercel login`

### Python Integration Packages

Install all at once:
```bash
pip install -r requirements-integrations.txt
```

Or install individually:

- [ ] **Notion SDK**
  - `pip install notion-client>=2.2.1`
  - Verify: `python -c "import notion_client"`

- [ ] **Asana SDK**
  - `pip install asana>=1.0.0`
  - Verify: `python -c "import asana"`

- [ ] **Google Workspace SDK**
  - `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
  - Verify: `python -c "from google.oauth2 import service_account"`

- [ ] **Azure SDK**
  - `pip install azure-identity azure-mgmt-resource azure-mgmt-compute azure-mgmt-storage azure-storage-blob azure-keyvault-secrets`
  - Verify: `python -c "from azure.identity import DefaultAzureCredential"`

- [ ] **Prometheus Client**
  - `pip install prometheus-client`
  - Verify: `python -c "import prometheus_client"`

- [ ] **Database Drivers**
  - `pip install psycopg2-binary redis sqlalchemy alembic`
  - Verify: `python -c "import psycopg2; import redis; import sqlalchemy"`

### Node.js Packages

- [ ] **Project Dependencies**
  - `npm install`
  - Installs all packages from package.json

- [ ] **Global Tools**
  - `npm install -g vercel`
  - `npm install -g n8n`

### Monitoring Tools (Docker)

- [ ] **Prometheus**
  - Via docker-compose: `docker-compose up prometheus`
  - Access: http://localhost:9090

- [ ] **Grafana**
  - Via docker-compose: `docker-compose up grafana`
  - Access: http://localhost:3000
  - Default: admin/admin (change on first login)

- [ ] **Alertmanager**
  - Via docker-compose: `docker-compose up alertmanager`
  - Access: http://localhost:9093

### Workflow Automation

- [ ] **N8N**
  - Option 1: `npm install -g n8n`
  - Option 2: Docker: `docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n`
  - Access: http://localhost:5678

## Environment Variables Setup

Create `.env` file in project root with:

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

## Quick Start Commands

### 1. Install All Dependencies
```powershell
# Run as Administrator
.\install_all_dependencies.ps1
```

### 2. Install Python Packages
```bash
python install_python_packages.py
# OR
pip install -r requirements-integrations.txt
```

### 3. Install Node.js Packages
```powershell
.\install_node_packages.ps1
# OR
npm install
```

### 4. Start Docker Services
```bash
docker-compose up -d
```

### 5. Verify Installation
```powershell
.\check_dependencies.ps1
```

## Verification Tests

### Test Python Imports
```python
# Test all integrations
python -c "import notion_client; print('Notion OK')"
python -c "import asana; print('Asana OK')"
python -c "from google.oauth2 import service_account; print('Google OK')"
python -c "from azure.identity import DefaultAzureCredential; print('Azure OK')"
python -c "import prometheus_client; print('Prometheus OK')"
python -c "import redis; print('Redis OK')"
python -c "import psycopg2; print('PostgreSQL OK')"
```

### Test CLI Tools
```bash
python --version
node --version
docker --version
az --version
gh --version
vercel --version
n8n --version
```

### Test Docker Services
```bash
docker-compose ps
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana
curl http://localhost:5678  # N8N
```

## Next Steps

1. **Configure Environment Variables**
   - Copy `.env.example` to `.env`
   - Fill in all API keys and credentials

2. **Set Up API Access**
   - Azure: Run `az login` and configure service principal
   - GitHub: Run `gh auth login`
   - Vercel: Run `vercel login`
   - Notion: Get API key from https://www.notion.so/my-integrations
   - Asana: Get access token from https://app.asana.com/0/my-apps
   - Google Workspace: Create OAuth credentials in Google Cloud Console

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Run Application**
   ```bash
   poetry install
   poetry run python -m mycosoft_mas
   ```

5. **Access Dashboards**
   - MAS API: http://localhost:8000
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090
   - N8N: http://localhost:5678

## Troubleshooting

### Python Version Issues
- Ensure Python 3.11+ is installed
- Use `python3.11` explicitly if multiple versions exist
- Check PATH environment variable

### Docker Issues
- Ensure Docker Desktop is running
- Check with `docker info`
- Restart Docker Desktop if needed

### Port Conflicts
- PostgreSQL: Use port 5433 for MAS (configured in docker-compose.yml)
- Check ports: `netstat -ano | findstr :PORT`

### Authentication Issues
- Azure: `az login` then `az account show`
- GitHub: `gh auth status`
- Verify API keys in `.env` file

### Package Installation Failures
- Upgrade pip: `python -m pip install --upgrade pip`
- Use virtual environment: `python -m venv venv`
- Try installing packages individually

## Support Resources

- **Dependency Tree:** See `DEPENDENCY_TREE.md`
- **Integration Guide:** See `INTEGRATION_SETUP_GUIDE.md`
- **System Diagnostics:** See `SYSTEM_DIAGNOSTICS_REPORT.md`

## Notes

- **Proxmox, Ubiquity, Unify:** These are server-side infrastructure tools and not required for local development
- **Docker Alternative:** Most services can run via Docker instead of local installation
- **Poetry vs pip:** Poetry is recommended for Python dependency management, but pip works too
- **Virtual Environment:** Consider using a virtual environment for Python packages
