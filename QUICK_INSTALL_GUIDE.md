# Quick Install Guide - Mycosoft MAS

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Core Tools (Run as Administrator)

```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install essentials
choco install python311 nodejs-lts docker-desktop git -y
```

### Step 2: Install Python Packages

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install all integration packages
pip install -r requirements-integrations.txt

# OR use the automated script
python install_python_packages.py
```

### Step 3: Install Node.js Packages

```bash
# Install project dependencies
npm install

# Install global tools
npm install -g vercel n8n
```

### Step 4: Start Docker Services

```bash
# Start all services (PostgreSQL, Redis, Prometheus, Grafana, Qdrant)
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 5: Configure Environment

```bash
# Copy example env file
copy .env.example .env

# Edit .env and add your API keys:
# - Azure credentials
# - Notion API key
# - Asana token
# - Google Workspace credentials
# - N8N webhook URL
```

## 📦 What Gets Installed

### System Tools
- ✅ Python 3.11+
- ✅ Node.js LTS
- ✅ Docker Desktop
- ✅ Git

### Python Packages
- ✅ FastAPI, Uvicorn, Pydantic
- ✅ Notion SDK
- ✅ Asana SDK
- ✅ Google Workspace SDK
- ✅ Azure SDK
- ✅ Prometheus Client
- ✅ Database drivers (PostgreSQL, Redis)

### Node.js Packages
- ✅ Next.js, React
- ✅ UI components (Radix UI)
- ✅ State management (Zustand, React Query)

### Docker Services
- ✅ PostgreSQL (port 5433)
- ✅ Redis (port 6379)
- ✅ Qdrant (port 6333)
- ✅ Prometheus (port 9090)
- ✅ Grafana (port 3000)

### Global Tools
- ✅ Azure CLI (`az`)
- ✅ GitHub CLI (`gh`)
- ✅ Vercel CLI (`vercel`)
- ✅ N8N (`n8n`)

## 🔧 Manual Installation (If Scripts Fail)

### Python Packages
```bash
pip install notion-client asana google-api-python-client google-auth-httplib2 google-auth-oauthlib azure-identity azure-mgmt-resource azure-mgmt-compute azure-mgmt-storage azure-storage-blob azure-keyvault-secrets prometheus-client redis psycopg2-binary sqlalchemy alembic fastapi uvicorn pydantic python-dotenv
```

### Cloud CLIs
```powershell
# Azure CLI
choco install azure-cli

# GitHub CLI
choco install gh

# Vercel CLI
npm install -g vercel
```

### Database Tools (Optional - Docker Recommended)
```powershell
# PostgreSQL
choco install postgresql

# Redis
choco install redis-64
```

## ✅ Verification

### Check Installed Tools
```powershell
python --version
node --version
docker --version
git --version
az --version
gh --version
vercel --version
n8n --version
```

### Test Python Imports
```python
python -c "import notion_client; print('✓ Notion')"
python -c "import asana; print('✓ Asana')"
python -c "from google.oauth2 import service_account; print('✓ Google')"
python -c "from azure.identity import DefaultAzureCredential; print('✓ Azure')"
python -c "import prometheus_client; print('✓ Prometheus')"
```

### Test Docker Services
```bash
# Check services
docker-compose ps

# Test endpoints
curl http://localhost:9090  # Prometheus
curl http://localhost:3000   # Grafana
curl http://localhost:5678   # N8N
```

## 🔑 API Keys Setup

### Azure
1. Run `az login`
2. Get credentials from Azure Portal
3. Set environment variables:
   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `AZURE_SUBSCRIPTION_ID`

### Notion
1. Go to https://www.notion.so/my-integrations
2. Create new integration
3. Copy API key to `NOTION_API_KEY`
4. Get database ID from Notion page URL

### Asana
1. Go to https://app.asana.com/0/my-apps
2. Create personal access token
3. Set `ASANA_ACCESS_TOKEN`
4. Get workspace ID from Asana

### Google Workspace
1. Go to Google Cloud Console
2. Create project and enable APIs
3. Create OAuth 2.0 credentials
4. Download credentials JSON
5. Set `GOOGLE_APPLICATION_CREDENTIALS` to file path

### GitHub
1. Run `gh auth login`
2. Follow prompts

### Vercel
1. Run `vercel login`
2. Follow prompts

## 🐳 Docker Services

### Start All Services
```bash
docker-compose up -d
```

### Stop All Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Restart Specific Service
```bash
docker-compose restart postgres
docker-compose restart redis
```

## 📚 Documentation Files

- **`DEPENDENCY_TREE.md`** - Complete dependency documentation
- **`INSTALLATION_REPORT.md`** - Detailed installation report
- **`INTEGRATION_SETUP_GUIDE.md`** - Integration-specific setup
- **`QUICK_INSTALL_GUIDE.md`** - This file

## 🆘 Troubleshooting

### Python Not Found
```powershell
# Refresh environment
refreshenv

# Check PATH
$env:Path

# Reinstall Python
choco install python311 -y --force
```

### Docker Not Running
```powershell
# Start Docker Desktop manually
# Or check service
Get-Service docker

# Restart Docker
Restart-Service docker
```

### Port Already in Use
```powershell
# Check what's using the port
netstat -ano | findstr :5433

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in docker-compose.yml
```

### Package Installation Fails
```bash
# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# Use virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements-integrations.txt
```

## 🎯 Next Steps

1. ✅ Install all dependencies (this guide)
2. ⏭️ Configure `.env` file with API keys
3. ⏭️ Start Docker services
4. ⏭️ Run application: `poetry run python -m mycosoft_mas`
5. ⏭️ Access dashboards and verify integrations

## 📞 Support

- Check `DEPENDENCY_TREE.md` for detailed information
- Review `INSTALLATION_REPORT.md` for installation status
- See `INTEGRATION_SETUP_GUIDE.md` for API setup
