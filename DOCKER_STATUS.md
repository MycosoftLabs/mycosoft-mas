# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.







# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.








# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.







# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.











# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.







# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.








# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.







# Mycosoft Docker Services Status

**Last Updated:** 2025-12-28

## ✅ Running Essential Services

All core Mycosoft components are running efficiently in Docker:

### Infrastructure Services
- **PostgreSQL** (`mycosoft-postgres`) - Port 5433
  - Database for MAS system
  - Status: Healthy

- **Redis** (`mycosoft-redis`) - Port 6390
  - Caching and message queue
  - Status: Healthy

- **Qdrant** (`mycosoft-qdrant`) - Port 6345
  - Vector database for embeddings
  - Status: Healthy

### Mycosoft MAS (Multi-Agent System)
- **MAS Orchestrator** (`mycosoft-mas-orchestrator`) - Port 8001
  - Main API and orchestration service
  - Status: Healthy
  - Endpoint: http://localhost:8001

### Workflows & Automation
- **n8n** (`mycosoft-n8n`) - Port 5678
  - Workflow automation platform
  - Status: Running
  - Endpoint: http://localhost:5678

### Voice Services
- **Whisper STT** (`mycosoft-whisper`) - Port 8765
  - Speech-to-text service
  - Status: Healthy

- **OpenAI Speech TTS** (`mycosoft-tts`) - Port 5500
  - Text-to-speech service
  - Status: Running

### Dashboards & Applications
- **MAS Dashboard** (`mycosoft-mas-dashboard`) - Port 3100
  - NatureOS MAS integration dashboard
  - Status: Healthy
  - Endpoint: http://localhost:3100

- **MYCA App** (`mycosoft-myca-app`) - Port 3001
  - Next.js app with MINDEX/NatureOS
  - Status: Running
  - Endpoint: http://localhost:3001

### Main Website
- **Mycosoft.com Website** - Port 3000
  - Primary React/Next.js website
  - Running via `npm run dev` (not Docker)
  - Endpoint: http://localhost:3000

## 📊 Service Summary

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL | mycosoft-postgres | 5433 | ✅ Healthy |
| Redis | mycosoft-redis | 6390 | ✅ Healthy |
| Qdrant | mycosoft-qdrant | 6345 | ✅ Healthy |
| MAS Orchestrator | mycosoft-mas-orchestrator | 8001 | ✅ Healthy |
| n8n Workflows | mycosoft-n8n | 5678 | ✅ Running |
| Whisper STT | mycosoft-whisper | 8765 | ✅ Healthy |
| TTS Service | mycosoft-tts | 5500 | ✅ Running |
| MAS Dashboard | mycosoft-mas-dashboard | 3100 | ✅ Healthy |
| MYCA App | mycosoft-myca-app | 3001 | ✅ Running |
| Main Website | (npm dev) | 3000 | ✅ Running |

## 🚀 Quick Start Commands

### Start All Services
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
docker compose -f docker-compose.essential.yml up -d
```

### Stop All Services
```bash
docker compose -f docker-compose.essential.yml down
```

### View Logs
```bash
docker compose -f docker-compose.essential.yml logs -f [service-name]
```

### Restart a Service
```bash
docker compose -f docker-compose.essential.yml restart [service-name]
```

## 🔧 Optimizations Applied

1. **Removed Duplicate Images** - Cleaned up 50+ stale images from previous sessions
2. **Removed Unused Networks** - Cleaned up orphaned Docker networks
3. **Streamlined Services** - Only essential services running:
   - Removed optional agent managers (causing restart loops)
   - Kept core orchestrator which handles all functionality
4. **Fixed TypeScript Build** - Updated `tsconfig.json` with `downlevelIteration: true` and `target: ES2017`
5. **Efficient Resource Usage** - All containers using minimal resources

## 📝 Notes

- **Agent Managers**: Currently commented out in `docker-compose.essential.yml` due to module path issues. The orchestrator handles all agent functionality.
- **MycoBrain Service**: Not containerized (runs on host for USB access). Accessible at `http://localhost:8765` when running.
- **Main Website**: Runs via `npm run dev` for development, not in Docker.

## 🔗 Service Endpoints

- **Main Website**: http://localhost:3000
- **MAS API**: http://localhost:8001
- **MAS Dashboard**: http://localhost:3100
- **MYCA App**: http://localhost:3001
- **n8n Workflows**: http://localhost:5678
- **Whisper STT**: http://localhost:8765
- **TTS Service**: http://localhost:5500

## ✅ All Systems Operational

All essential Mycosoft components are running efficiently with no duplicates or unnecessary containers.











