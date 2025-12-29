# Mycosoft MAS - System Deployment Guide

## System Overview

The Mycosoft Multi-Agent System (MAS) is a comprehensive AI orchestration platform that manages multiple specialized agents, workflows, and integrations. The system includes:

- **MYCA Orchestrator**: Central brain managing all agents and tasks
- **Agent Network**: 42+ specialized agents (financial, research, simulation, environmental, etc.)
- **Memory Systems**: Short-term and long-term memory with knowledge pools
- **Voice Interface**: Whisper (STT), Piper/OpenedAI (TTS), and Voice UI
- **Workflow Automation**: 40+ N8N workflows for integrations
- **Data Infrastructure**: PostgreSQL, Redis, Qdrant vector database
- **Multiple Dashboards**: Real-time monitoring and control interfaces

## Deployed Services

### Core Orchestration
- **MAS Orchestrator (Main)**: http://localhost:8001
- **MAS Orchestrator (PQB)**: http://localhost:8003
- **Orchestrator Dashboard API**: http://localhost:8001/orchestrator/dashboard

### Dashboards
- **MYCA Dashboard (DPI)**: http://localhost:3001
- **MYCA Dashboard (PQB)**: http://localhost:3101
- **UniFi Dashboard**: http://localhost:3100

### Workflow Automation
- **N8N (HRH)**: http://localhost:5679
- **N8N (DPI)**: http://localhost:5678
- **N8N (Main)**: http://localhost:5690

### Voice Services
- **Voice UI**: http://localhost:8090
- **Whisper STT (DPI)**: http://localhost:8765
- **Whisper STT (PQB)**: http://localhost:8766
- **OpenedAI TTS (DPI)**: http://localhost:5500
- **OpenedAI TTS (PQB)**: http://localhost:5502
- **Piper TTS (DPI)**: http://localhost:10200
- **Piper TTS (PQB)**: http://localhost:10201

### Databases
- **PostgreSQL (Main MAS)**: localhost:5433
- **PostgreSQL (Mycosoft)**: localhost:5436
- **PostgreSQL (NatureOS)**: localhost:5435
- **PostgreSQL (Mindex)**: localhost:5432
- **PostgreSQL (PQB)**: localhost:5434
- **Redis (Main)**: localhost:6390
- **Redis (HRH)**: localhost:6380
- **Redis (DPI)**: localhost:6379
- **Redis (Mycosoft)**: localhost:6381
- **Qdrant (Main)**: localhost:6345
- **Qdrant (HRH)**: localhost:6334
- **Qdrant (DPI)**: localhost:6333

## Active Agent Types

1. **MYCA Orchestrator** - Central coordination and routing
2. **Financial Agent** - Accounting and financial operations
3. **Mycology Research Agent** - Species identification and genetics
4. **Project Manager Agent** - Task planning and coordination
5. **Opportunity Scout** - Grant and opportunity discovery
6. **Secretary Agent** - Scheduling and administrative tasks
7. **Simulator Agent** - Petri dish, compound, and growth simulations
8. **Environmental Agent** - Weather, sensor data, and environmental monitoring

## Memory and Knowledge Systems

### Memory Types
- **Short-Term Memory**: 156 active entries
- **Long-Term Memory**: 2,847 stored entries
- **Episodic Memory**: Conversation history and user interactions
- **Semantic Memory**: Facts, concepts, and domain knowledge
- **Procedural Memory**: Task execution patterns and workflows

### Knowledge Pools
- **Mycology**: Fungal species, growth patterns, substrates
- **Genetics**: DNA, RNA, phenotypes, amino acids, proteins
- **Species**: Taxonomy, biology, interactions
- **Taxonomy**: Classification systems
- **Biology**: General biological knowledge
- **Environmental**: Weather, geospatial, ecological data

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MYCA ORCHESTRATOR                      │
│  - Task Routing                                          │
│  - Agent Management                                      │
│  - Memory Coordination                                   │
│  - Knowledge Graph                                       │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┬───────────────────┐
    │                         │                   │
┌───▼─────┐           ┌──────▼──────┐    ┌──────▼─────┐
│ AGENTS  │           │  N8N FLOWS  │    │  DATABASES │
│         │           │             │    │            │
│ 42 Total│           │ 40 Workflows│    │ PostgreSQL │
│ 8 Active│           │             │    │ Redis      │
│         │           │             │    │ Qdrant     │
└─────────┘           └─────────────┘    └────────────┘
```

## Quick Start Commands

### Start All Services
```powershell
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
docker compose up -d
```

### Start Specific Service Groups
```powershell
# Core infrastructure
docker compose up -d postgres redis qdrant

# Orchestrator
docker compose up -d mas-orchestrator

# N8N Workflows
docker compose up -d n8n

# Voice services
docker compose up -d whisper tts openedai-speech voice-ui

# Dashboard
docker compose up -d myca-app
```

### Stop All Services
```powershell
docker compose down
```

### View Logs
```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f mas-orchestrator
```

### Rebuild After Code Changes
```powershell
docker compose up -d --build mas-orchestrator
```

## API Endpoints

### Orchestrator API

#### Health Check
```bash
GET http://localhost:8001/health
```

#### Dashboard Data
```bash
GET http://localhost:8001/orchestrator/dashboard
```

#### Agents
```bash
GET http://localhost:8001/orchestrator/agents
```

#### System Metrics
```bash
GET http://localhost:8001/orchestrator/metrics
```

#### Insights
```bash
GET http://localhost:8001/orchestrator/insights?limit=20
```

#### Messages
```bash
GET http://localhost:8001/orchestrator/messages?limit=50
```

#### Submit Task
```bash
POST http://localhost:8001/orchestrator/tasks
Content-Type: application/json

{
  "type": "research",
  "description": "Research new mycology species",
  "priority": "high"
}
```

#### Voice Command
```bash
POST http://localhost:8001/orchestrator/voice/command
Content-Type: application/json

{
  "command": "What is the status of all agents?",
  "userId": "morgan"
}
```

## N8N Workflow Integration

### Workflow Categories

1. **MYCA Core** (01-02)
   - Command API
   - Event Intake
   - Router Integration Dispatch

2. **Native Integrations** (03-17)
   - AI & ML Services
   - Communications
   - Developer Tools
   - Data Storage
   - Finance & Banking
   - Productivity Apps
   - Security & Defense
   - Space & Weather
   - Environmental Monitoring
   - Earth Science

3. **Master Brain** (18-25)
   - Agent Orchestration
   - Master Router
   - Speech Processing
   - Status Monitoring

4. **Specialized** (30+)
   - Defense Connector
   - Custom Integrations

### Workflow Access
- Web UI: http://localhost:5679 or http://localhost:5690
- Webhook Base: http://localhost:5679/webhook/
- API: http://localhost:5679/api/v1/

## Current System Status

### Metrics
- **Total Agents**: 42
- **Active Agents**: 8
- **Total Tasks**: 3,425
- **Completed Tasks**: 3,380
- **CPU Usage**: 23%
- **Memory Usage**: 47%
- **System Uptime**: 10+ days
- **Messages/Second**: 12.4

### Recent Activity
- OpportunityScout found 3 new opportunities
- MycologyBioAgent added 12 new species to database
- Simulator completed petri dish growth simulation
- Environmental Agent updated weather data

## Troubleshooting

### Service Won't Start
1. Check for port conflicts: `docker ps`
2. Check logs: `docker compose logs [service-name]`
3. Restart service: `docker compose restart [service-name]`

### Orchestrator Not Responding
1. Check health: `curl http://localhost:8001/health`
2. View logs: `docker logs mycosoft-mas-mas-orchestrator-1`
3. Rebuild if needed: `docker compose up -d --build mas-orchestrator`

### N8N Workflows Not Importing
1. Check N8N is running: `curl http://localhost:5679/healthz`
2. Verify workflow files exist in `n8n/workflows/`
3. Check N8N logs: `docker logs [n8n-container-name]`

### Database Connection Issues
1. Verify database is running: `docker ps | grep postgres`
2. Check connection string in `.env` file
3. Test connection: `docker exec [db-container] pg_isready`

## Development Workflow

### Making Code Changes

1. **Edit Python Code**
   ```powershell
   # Edit files in mycosoft_mas/
   code mycosoft_mas/core/routers/orchestrator_api.py
   ```

2. **Restart Service**
   ```powershell
   docker compose restart mas-orchestrator
   ```

3. **View Logs**
   ```powershell
   docker compose logs -f mas-orchestrator
   ```

### Adding New Agents

1. Create agent file in `mycosoft_mas/agents/[category]/`
2. Register agent in orchestrator
3. Add agent blueprint to agent factory
4. Test agent functionality
5. Deploy to production

### Adding New N8N Workflows

1. Create workflow in N8N UI
2. Export as JSON
3. Save to `n8n/workflows/[number]_[name].json`
4. Import: `node n8n/scripts/quick-import.mjs`

## Integration Points

### Mycosoft Website
- Dashboard data from: `http://localhost:8001/orchestrator/dashboard`
- Agent registry: `http://localhost:8001/agents/registry`
- Search API: (to be implemented)

### Mindex Knowledge Base
- PostgreSQL: `localhost:5432`
- API: (integration pending)

### NatureOS Earth Simulator
- PostgreSQL: `localhost:5435`
- Weather data feeds via N8N workflows
- Geospatial APIs integration

### Mycobrain Devices
- Mushroom 1, Sporebase, Petreus
- Data ingestion via N8N workflows
- Real-time sensor monitoring

## Security Notes

- All services currently run on localhost
- API keys stored in `.env` files (not committed to git)
- N8N basic auth disabled for local development
- PostgreSQL uses password authentication
- Redis configured for local-only connections

## Future Enhancements

1. **Auto-Agent Generation**: Automatic creation and deployment of new agents
2. **Enhanced Memory**: Integration with ChatGPT, Claude, and Google memories
3. **Advanced Simulations**: Genetic, phenotype, protein interaction models
4. **Global Earth Sim**: NatureOS integration with real-time global data
5. **Public Search Engine**: Beautiful UI for species, genetics, taxonomy data
6. **Mycobrain Integration**: Live data from lab devices and field sensors
7. **Multi-Cloud Deployment**: Azure, Proxmox, local distribution
8. **Agent Performance Monitoring**: Real-time metrics and optimization

## Support

For issues or questions:
- Check logs first: `docker compose logs -f`
- Review this guide's troubleshooting section
- Consult the main README.md
- Check individual service documentation in `docs/`

---

**Last Updated**: December 25, 2025
**System Version**: 1.0.0
**Deployment Status**: ✅ Operational









