# Azure Failover and Sync Preparation

This document describes the Azure preparation for MYCA, including data sync and failover capabilities.

## Overview

While MYCA runs locally on the Proxmox cluster, Azure serves as:

1. **Disaster Recovery** - Failover if local infrastructure fails
2. **Scaling** - Burst capacity for heavy workloads
3. **Geographic Distribution** - Serve users globally
4. **Backup Storage** - Off-site backup for critical data

## Azure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Cloud                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ Azure Container  │    │ Azure Database   │                  │
│  │ Instances        │    │ for PostgreSQL   │                  │
│  │ (MYCA Standby)   │    │ (Replica)        │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                             │
│           └───────────┬───────────┘                             │
│                       │                                          │
│              ┌────────┴────────┐                                │
│              │  Azure Front    │                                │
│              │  Door           │                                │
│              └────────┬────────┘                                │
│                       │                                          │
│  ┌──────────────────┐ │ ┌──────────────────┐                   │
│  │ Azure Blob       │ │ │ Azure Container  │                   │
│  │ Storage          │ │ │ Registry         │                   │
│  │ (Backups)        │ │ │ (Images)         │                   │
│  └──────────────────┘ │ └──────────────────┘                   │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                   ┌────┴────┐
                   │ Internet │
                   └────┬────┘
                        │
┌───────────────────────┼──────────────────────────────────────────┐
│                       │        Local Infrastructure              │
│              ┌────────┴────────┐                                │
│              │  Cloudflare     │                                │
│              │  Tunnel         │                                │
│              └────────┬────────┘                                │
│                       │                                          │
│  ┌──────────────────┐ │ ┌──────────────────┐                   │
│  │ MYCA Core VM     │◄┴►│ PostgreSQL       │                   │
│  │ (Primary)        │   │ (Primary)        │                   │
│  └──────────────────┘   └──────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Mapping Local to Azure

| Local Resource | Azure Equivalent |
|----------------|------------------|
| Proxmox VMs | Azure Container Instances |
| PostgreSQL (NAS) | Azure Database for PostgreSQL |
| Qdrant (NAS) | Azure Blob + ACI |
| 26TB NAS | Azure Blob Storage |
| Cloudflare Tunnel | Azure Front Door |
| HashiCorp Vault | Azure Key Vault |

## Step 1: Azure Prerequisites

### Create Resource Group

```bash
# Login to Azure
az login

# Create resource group
az group create --name mycosoft-failover --location eastus
```

### Create Storage Account

```bash
# Create storage account for backups
az storage account create \
  --name mycosoftbackups \
  --resource-group mycosoft-failover \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2
```

### Create Container Registry

```bash
# Create container registry
az acr create \
  --name mycosoftacr \
  --resource-group mycosoft-failover \
  --sku Basic \
  --admin-enabled true
```

## Step 2: Database Replication

### Setup Azure Database for PostgreSQL

```bash
# Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --name mycosoft-db \
  --resource-group mycosoft-failover \
  --location eastus \
  --admin-user mycaadmin \
  --admin-password "${POSTGRES_ADMIN_PASSWORD}" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 128 \
  --version 16

# Create databases
az postgres flexible-server db create \
  --resource-group mycosoft-failover \
  --server-name mycosoft-db \
  --database-name mas

az postgres flexible-server db create \
  --resource-group mycosoft-failover \
  --server-name mycosoft-db \
  --database-name mindex
```

### Configure Logical Replication

On local PostgreSQL:

```sql
-- Enable logical replication
ALTER SYSTEM SET wal_level = logical;
ALTER SYSTEM SET max_replication_slots = 4;
ALTER SYSTEM SET max_wal_senders = 4;

-- Create publication
CREATE PUBLICATION myca_publication FOR ALL TABLES;
```

On Azure PostgreSQL:

```sql
-- Create subscription
CREATE SUBSCRIPTION myca_subscription
  CONNECTION 'host=your-tunnel-endpoint port=5432 dbname=mas user=replicator password=xxx'
  PUBLICATION myca_publication;
```

## Step 3: Backup Sync

### Configure Azure Blob Backup

Create backup script:

```bash
#!/bin/bash
# azure_backup_sync.sh - Sync local backups to Azure

STORAGE_ACCOUNT="mycosoftbackups"
CONTAINER="backups"
LOCAL_BACKUP_PATH="/mnt/mycosoft/backups"

# Get storage key
STORAGE_KEY=$(az storage account keys list \
  --resource-group mycosoft-failover \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' -o tsv)

# Sync backups
azcopy sync "$LOCAL_BACKUP_PATH" \
  "https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER}" \
  --recursive
```

### Schedule Sync

Add to crontab:

```cron
# Sync backups to Azure daily at 4 AM
0 4 * * * /opt/myca/scripts/azure_backup_sync.sh >> /var/log/azure-sync.log 2>&1
```

## Step 4: Container Image Sync

Push images to Azure Container Registry:

```bash
# Login to ACR
az acr login --name mycosoftacr

# Tag and push images
docker tag mycosoft/mas-orchestrator:latest mycosoftacr.azurecr.io/mas-orchestrator:latest
docker push mycosoftacr.azurecr.io/mas-orchestrator:latest

docker tag mycosoft/website:latest mycosoftacr.azurecr.io/website:latest
docker push mycosoftacr.azurecr.io/website:latest
```

## Step 5: Standby Container Instances

Create standby ACI deployment (stopped by default):

```bash
# Create MYCA orchestrator ACI (stopped)
az container create \
  --resource-group mycosoft-failover \
  --name myca-orchestrator-standby \
  --image mycosoftacr.azurecr.io/mas-orchestrator:latest \
  --registry-login-server mycosoftacr.azurecr.io \
  --registry-username mycosoftacr \
  --registry-password "${ACR_PASSWORD}" \
  --cpu 2 \
  --memory 4 \
  --ports 8001 \
  --environment-variables \
    MAS_ENV=production \
    DATABASE_URL="postgresql://mycaadmin:xxx@mycosoft-db.postgres.database.azure.com:5432/mas" \
  --restart-policy OnFailure \
  --no-wait
  
# Stop immediately (standby)
az container stop \
  --resource-group mycosoft-failover \
  --name myca-orchestrator-standby
```

## Step 6: Azure Front Door (Optional)

For automatic failover:

```bash
# Create Front Door profile
az afd profile create \
  --profile-name mycosoft-fd \
  --resource-group mycosoft-failover \
  --sku Standard_AzureFrontDoor

# Add endpoints for local and Azure
az afd endpoint create \
  --resource-group mycosoft-failover \
  --profile-name mycosoft-fd \
  --endpoint-name mycosoft-main \
  --enabled-state Enabled
```

## Failover Procedures

### Automatic Health Checks

Configure monitoring to detect local failure:

```yaml
# Azure Monitor action group
- alert: LocalMYCADown
  condition: HTTPPingFailed for 5 minutes
  actions:
    - Start Azure standby containers
    - Switch DNS to Azure Front Door
    - Notify Morgan
```

### Manual Failover

```bash
# 1. Start Azure containers
az container start \
  --resource-group mycosoft-failover \
  --name myca-orchestrator-standby

# 2. Update Cloudflare DNS (or use Front Door)
# Point mycosoft.com to Azure IP

# 3. Verify
curl https://mycosoft.com/health
```

### Failback to Local

```bash
# 1. Sync data back from Azure
pg_dump -h mycosoft-db.postgres.database.azure.com -U mycaadmin mas | \
  psql -h localhost -U mas mas

# 2. Stop Azure containers
az container stop \
  --resource-group mycosoft-failover \
  --name myca-orchestrator-standby

# 3. Update DNS back to local Cloudflare Tunnel

# 4. Verify
curl https://mycosoft.com/health
```

## Cost Optimization

| Resource | Monthly Cost (estimate) |
|----------|------------------------|
| Storage Account (100GB) | ~$2 |
| Container Registry (Basic) | ~$5 |
| PostgreSQL (Stopped) | ~$0 |
| Container Instances (Stopped) | ~$0 |
| **Standby Total** | **~$7/month** |

When activated:

| Resource | Hourly Cost |
|----------|-------------|
| PostgreSQL (B1ms) | ~$0.03 |
| Container Instances (2 vCPU, 4GB) | ~$0.10 |
| **Active Total** | **~$0.13/hour** |

## Monitoring Azure Resources

```bash
# Check container status
az container show \
  --resource-group mycosoft-failover \
  --name myca-orchestrator-standby \
  --query "instanceView.state"

# Check database status
az postgres flexible-server show \
  --resource-group mycosoft-failover \
  --name mycosoft-db \
  --query "state"

# List all resources
az resource list \
  --resource-group mycosoft-failover \
  --output table
```

## Security Considerations

1. **Azure Key Vault**: Store all secrets in Key Vault, not in container environment variables
2. **Private Endpoints**: Use private endpoints for PostgreSQL
3. **Network Security Groups**: Restrict access to known IPs
4. **Managed Identity**: Use managed identity for container authentication
