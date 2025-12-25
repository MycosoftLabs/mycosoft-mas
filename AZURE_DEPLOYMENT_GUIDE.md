# Azure Deployment Guide for MYCA MAS

This guide covers deploying the complete MYCA Multi-Agent System to Azure, including the dashboard, MAS backend, and all integrations (MINDEX, NATUREOS, WEBSITE).

## Prerequisites

1. **Azure Account** with active subscription
2. **Azure CLI** installed and logged in
3. **Docker Desktop** (for local testing)
4. **Git** access to all repositories

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Azure Container Instances           │
├─────────────────────────────────────────────────┤
│  - MAS Orchestrator (Port 8001)                │
│  - Dashboard (Port 3000)                        │
│  - n8n (Port 5678)                              │
│  - ElevenLabs Proxy (Port 5501)                 │
├─────────────────────────────────────────────────┤
│              Azure Database for PostgreSQL      │
├─────────────────────────────────────────────────┤
│  - MINDEX Database (PostGIS enabled)            │
│  - NATUREOS Database                            │
│  - MAS Database                                 │
├─────────────────────────────────────────────────┤
│              Azure Container Registry            │
├─────────────────────────────────────────────────┤
│  - Docker images for all services               │
└─────────────────────────────────────────────────┘
```

## Step 1: Prepare Azure Resources

### 1.1 Create Resource Group

```powershell
az group create --name mycosoft-mas-rg --location eastus
```

### 1.2 Create Container Registry

```powershell
az acr create --resource-group mycosoft-mas-rg --name mycosoftmas --sku Basic
```

### 1.3 Create PostgreSQL Servers

```powershell
# MINDEX Database
az postgres flexible-server create \
  --resource-group mycosoft-mas-rg \
  --name mindex-db \
  --location eastus \
  --admin-user mindex \
  --admin-password <secure-password> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0

# NATUREOS Database
az postgres flexible-server create \
  --resource-group mycosoft-mas-rg \
  --name natureos-db \
  --location eastus \
  --admin-user natureos \
  --admin-password <secure-password> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0

# MAS Database
az postgres flexible-server create \
  --resource-group mycosoft-mas-rg \
  --name mas-db \
  --location eastus \
  --admin-user mas \
  --admin-password <secure-password> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0
```

### 1.4 Enable PostGIS Extension (for MINDEX)

```powershell
az postgres flexible-server parameter set \
  --resource-group mycosoft-mas-rg \
  --server-name mindex-db \
  --name shared_preload_libraries \
  --value "postgis"
```

## Step 2: Build and Push Docker Images

### 2.1 Login to Azure Container Registry

```powershell
az acr login --name mycosoftmas
```

### 2.2 Build and Push Images

```powershell
# MAS Orchestrator
docker build -t mycosoftmas.azurecr.io/mas-orchestrator:latest -f Dockerfile .
docker push mycosoftmas.azurecr.io/mas-orchestrator:latest

# Dashboard
cd unifi-dashboard
docker build -t mycosoftmas.azurecr.io/dashboard:latest -f Dockerfile .
docker push mycosoftmas.azurecr.io/dashboard:latest
cd ..

# n8n
docker build -t mycosoftmas.azurecr.io/n8n:latest -f n8n/Dockerfile .
docker push mycosoftmas.azurecr.io/n8n:latest

# ElevenLabs Proxy
docker build -t mycosoftmas.azurecr.io/elevenlabs-proxy:latest -f Dockerfile.elevenlabs .
docker push mycosoftmas.azurecr.io/elevenlabs-proxy:latest
```

## Step 3: Create Azure Container Instances

### 3.1 MAS Orchestrator

```powershell
az container create \
  --resource-group mycosoft-mas-rg \
  --name mas-orchestrator \
  --image mycosoftmas.azurecr.io/mas-orchestrator:latest \
  --registry-login-server mycosoftmas.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --dns-name-label mas-orchestrator \
  --ports 8001 \
  --environment-variables \
    MAS_ENV=production \
    DATABASE_URL=postgresql://mas:<password>@mas-db.postgres.database.azure.com:5432/mas \
    MINDEX_DATABASE_URL=postgresql://mindex:<password>@mindex-db.postgres.database.azure.com:5432/mindex \
    NATUREOS_API_URL=https://natureos-api.azurewebsites.net \
    WEBSITE_API_URL=https://mycosoft.com/api \
    ELEVENLABS_API_KEY=<key> \
    N8N_WEBHOOK_URL=https://n8n.azurewebsites.net \
  --cpu 2 \
  --memory 4
```

### 3.2 Dashboard

```powershell
az container create \
  --resource-group mycosoft-mas-rg \
  --name dashboard \
  --image mycosoftmas.azurecr.io/dashboard:latest \
  --registry-login-server mycosoftmas.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --dns-name-label myca-dashboard \
  --ports 3000 \
  --environment-variables \
    NODE_ENV=production \
    NEXT_PUBLIC_MAS_URL=https://mas-orchestrator.eastus.azurecontainer.io:8001 \
    MAS_BACKEND_URL=https://mas-orchestrator.eastus.azurecontainer.io:8001 \
    MINDEX_API_URL=https://mindex-api.azurewebsites.net \
    NATUREOS_API_URL=https://natureos-api.azurewebsites.net \
    WEBSITE_API_URL=https://mycosoft.com/api \
    ELEVENLABS_API_KEY=<key> \
    ELEVENLABS_VOICE_ID=aEO01A4wXwd1O8GPgGlF \
  --cpu 2 \
  --memory 4
```

## Step 4: Deploy Integration Services

### 4.1 MINDEX API (Azure App Service)

```powershell
# Create App Service Plan
az appservice plan create \
  --name mycosoft-app-plan \
  --resource-group mycosoft-mas-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group mycosoft-mas-rg \
  --plan mycosoft-app-plan \
  --name mindex-api \
  --deployment-container-image-name mycosoftmas.azurecr.io/mindex-api:latest

# Configure environment variables
az webapp config appsettings set \
  --resource-group mycosoft-mas-rg \
  --name mindex-api \
  --settings \
    DATABASE_URL=postgresql://mindex:<password>@mindex-db.postgres.database.azure.com:5432/mindex \
    MINDEX_API_PORT=8000
```

### 4.2 NATUREOS API (Azure App Service)

```powershell
az webapp create \
  --resource-group mycosoft-mas-rg \
  --plan mycosoft-app-plan \
  --name natureos-api \
  --deployment-container-image-name mycosoftmas.azurecr.io/natureos-api:latest

az webapp config appsettings set \
  --resource-group mycosoft-mas-rg \
  --name natureos-api \
  --settings \
    DATABASE_URL=postgresql://natureos:<password>@natureos-db.postgres.database.azure.com:5432/natureos \
    NATUREOS_API_PORT=8002
```

## Step 5: Configure Networking

### 5.1 Set Up Private Endpoints (Optional but Recommended)

```powershell
# Private endpoint for databases
az network private-endpoint create \
  --resource-group mycosoft-mas-rg \
  --name mindex-db-pe \
  --vnet-name mycosoft-vnet \
  --subnet default \
  --private-connection-resource-id <mindex-db-resource-id> \
  --group-id postgresqlServer \
  --connection-name mindex-db-connection
```

## Step 6: Environment Variables Summary

Create a `.env.azure` file with all production values:

```bash
# MAS
MAS_ENV=production
DATABASE_URL=postgresql://mas:<password>@mas-db.postgres.database.azure.com:5432/mas
REDIS_URL=redis://<redis-host>:6379/0

# MINDEX
MINDEX_DATABASE_URL=postgresql://mindex:<password>@mindex-db.postgres.database.azure.com:5432/mindex
MINDEX_API_URL=https://mindex-api.azurewebsites.net

# NATUREOS
NATUREOS_API_URL=https://natureos-api.azurewebsites.net
NATUREOS_API_KEY=<key>
NATUREOS_TENANT_ID=<tenant-id>

# Website
WEBSITE_API_URL=https://mycosoft.com/api

# ElevenLabs
ELEVENLABS_API_KEY=<key>
ELEVENLABS_VOICE_ID=aEO01A4wXwd1O8GPgGlF

# n8n
N8N_WEBHOOK_URL=https://n8n.azurewebsites.net
N8N_API_KEY=<key>
```

## Step 7: Verify Deployment

### 7.1 Test Services

```powershell
# Test MAS Orchestrator
curl https://mas-orchestrator.eastus.azurecontainer.io:8001/health

# Test Dashboard
curl https://myca-dashboard.eastus.azurecontainer.io:3000

# Test MINDEX API
curl https://mindex-api.azurewebsites.net/health

# Test NATUREOS API
curl https://natureos-api.azurewebsites.net/health
```

### 7.2 Run Production Smoke Tests

```powershell
.\scripts\prod_smoke_test.ps1 -DashboardUrl "https://myca-dashboard.eastus.azurecontainer.io:3000"
```

## Step 8: Monitoring and Logging

### 8.1 Enable Application Insights

```powershell
az monitor app-insights component create \
  --app mycosoft-mas-insights \
  --location eastus \
  --resource-group mycosoft-mas-rg
```

### 8.2 Configure Logging

```powershell
az container logs show \
  --resource-group mycosoft-mas-rg \
  --name mas-orchestrator \
  --follow
```

## Troubleshooting

### Common Issues

1. **Container won't start:**
   - Check logs: `az container logs --name <container-name>`
   - Verify environment variables
   - Check resource limits (CPU/memory)

2. **Database connection failures:**
   - Verify firewall rules allow Azure services
   - Check connection strings
   - Test connectivity from Azure Cloud Shell

3. **Image pull failures:**
   - Verify ACR credentials
   - Check image exists: `az acr repository list --name mycosoftmas`

## Cost Optimization

- Use **Azure Container Instances** for development/testing
- Use **Azure App Service** for production (better scaling)
- Use **Burstable** tier for databases (dev/test)
- Use **General Purpose** tier for production databases
- Enable **auto-shutdown** for non-production resources

## Next Steps

1. Set up CI/CD pipeline (GitHub Actions)
2. Configure custom domains
3. Set up SSL certificates
4. Configure backup strategies
5. Set up monitoring alerts

## Additional Resources

- [Azure Container Instances Documentation](https://docs.microsoft.com/azure/container-instances/)
- [Azure Database for PostgreSQL](https://docs.microsoft.com/azure/postgresql/)
- [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/)
