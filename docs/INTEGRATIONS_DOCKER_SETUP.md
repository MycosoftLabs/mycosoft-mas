# Docker Setup for MINDEX, NATUREOS, and WEBSITE

This guide explains how to set up MINDEX, NATUREOS, and the Mycosoft Website locally using Docker Desktop for integration testing with the MYCA MAS system.

## Overview

The integration services run in Docker containers and connect to the main MAS system:

- **MINDEX**: Mycological Index Database (PostgreSQL + PostGIS + API)
- **NATUREOS**: IoT Device Management Platform (API + Database)
- **WEBSITE**: Mycosoft Website (Next.js application)

## Prerequisites

1. **Docker Desktop** installed and running
2. **Git** for cloning repositories
3. **PowerShell** (Windows) or Bash (Linux/Mac)

## Quick Start

### Option 1: Automated Setup Script

```powershell
.\scripts\setup_integrations_docker.ps1
```

This script will:
1. Clone the MINDEX, NATUREOS, and Website repositories
2. Build Docker images
3. Start all services

### Option 2: Manual Setup

#### Step 1: Clone Repositories

```powershell
# Create integrations directory
mkdir integrations
cd integrations

# Clone MINDEX
git clone https://github.com/MycosoftLabs/mindex.git

# Clone NATUREOS
git clone https://github.com/MycosoftLabs/NatureOS.git

# Clone Website (if repository exists)
git clone https://github.com/MycosoftLabs/mycosoft-website.git
```

#### Step 2: Create Dockerfiles

Each integration needs a `Dockerfile` in its directory. See examples below.

#### Step 3: Start Services

```powershell
docker-compose -f docker-compose.integrations.yml up -d --build
```

## Service Details

### MINDEX

**Ports:**
- API: `8000`
- Database: `5432`

**Environment Variables:**
```bash
MINDEX_DB_USER=mindex
MINDEX_DB_PASSWORD=mindexpassword
MINDEX_DB_NAME=mindex
MINDEX_API_PORT=8000
MINDEX_API_KEY=your_api_key_here
```

**Database Connection:**
```
postgresql://mindex:mindexpassword@localhost:5432/mindex
```

**Health Check:**
```powershell
curl http://localhost:8000/health
```

### NATUREOS

**Ports:**
- API: `8002`
- Database: `5434` (to avoid conflict with MINDEX)

**Environment Variables:**
```bash
NATUREOS_API_PORT=8002
NATUREOS_API_KEY=your_api_key_here
NATUREOS_TENANT_ID=your_tenant_id
NATUREOS_DB_USER=natureos
NATUREOS_DB_PASSWORD=natureospassword
NATUREOS_DB_NAME=natureos
```

**API Endpoint:**
```
http://localhost:8002
```

**Health Check:**
```powershell
curl http://localhost:8002/health
```

### WEBSITE

**Ports:**
- Development: `3001` (to avoid conflict with dashboard on 3000)

**Environment Variables:**
```bash
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:3001/api
PORT=3001
```

**Access:**
```
http://localhost:3001
```

## Integration with MAS

Once services are running, update your MAS environment variables:

```bash
# In .env or docker-compose.yml
MINDEX_DATABASE_URL=postgresql://mindex:mindexpassword@localhost:5432/mindex
MINDEX_API_URL=http://localhost:8000

NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_api_key_here

WEBSITE_API_URL=http://localhost:3001/api
```

**Note:** If MAS is running in Docker, use `host.docker.internal` instead of `localhost`:

```bash
MINDEX_DATABASE_URL=postgresql://mindex:mindexpassword@host.docker.internal:5432/mindex
MINDEX_API_URL=http://host.docker.internal:8000
NATUREOS_API_URL=http://host.docker.internal:8002
WEBSITE_API_URL=http://host.docker.internal:3001/api
```

## Docker Compose File Structure

The `docker-compose.integrations.yml` file defines:

1. **MINDEX Services:**
   - `mindex-postgres`: PostgreSQL with PostGIS
   - `mindex-api`: MINDEX REST API

2. **NATUREOS Services:**
   - `natureos-postgres`: PostgreSQL database
   - `natureos-api`: NATUREOS REST API

3. **WEBSITE Service:**
   - `website-dev`: Next.js development server

All services are on the `mycosoft-integrations` network.

## Example Dockerfiles

### MINDEX API Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### NATUREOS API Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8002

# Run API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Website Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application
COPY . .

# Expose port
EXPOSE 3001

# Run dev server
CMD ["npm", "run", "dev", "--", "-p", "3001"]
```

## Troubleshooting

### Services Won't Start

1. **Check Docker Desktop is running:**
   ```powershell
   docker ps
   ```

2. **Check logs:**
   ```powershell
   docker-compose -f docker-compose.integrations.yml logs
   ```

3. **Verify repositories are cloned:**
   ```powershell
   ls integrations/mindex
   ls integrations/natureos
   ls integrations/website
   ```

### Port Conflicts

If ports are already in use:

1. **Check what's using the port:**
   ```powershell
   netstat -ano | findstr :8000
   ```

2. **Update ports in docker-compose.integrations.yml:**
   ```yaml
   ports:
     - "8001:8000"  # Change external port
   ```

3. **Update MAS environment variables accordingly**

### Database Connection Issues

1. **Wait for database to be ready:**
   ```powershell
   docker-compose -f docker-compose.integrations.yml ps
   ```
   Wait until `mindex-postgres` shows "healthy"

2. **Test connection:**
   ```powershell
   docker exec -it mindex-postgres psql -U mindex -d mindex -c "SELECT version();"
   ```

## Next Steps

1. **Test Integration:**
   ```python
   from mycosoft_mas.integrations import UnifiedIntegrationManager
   
   manager = UnifiedIntegrationManager()
   await manager.initialize()
   
   # Test MINDEX
   taxa = await manager.mindex.get_taxa(limit=5)
   
   # Test NATUREOS
   devices = await manager.natureos.list_devices()
   ```

2. **Update Dashboard:**
   - Connect dashboard to local MINDEX/NATUREOS APIs
   - Test data flow

3. **Deploy to Azure:**
   - Once local testing is complete, deploy to Azure
   - Update environment variables for production URLs

## Additional Resources

- [MINDEX Repository](https://github.com/MycosoftLabs/mindex)
- [NATUREOS Repository](https://github.com/MycosoftLabs/NatureOS)
- [MAS Integration Guide](../INTEGRATION_SETUP_GUIDE.md)
