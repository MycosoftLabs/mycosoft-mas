# Local Development Guide

This guide explains how to run the **Mycosoft MAS** (Multi-Agent System) locally using Docker.

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
  - Minimum Docker version: 20.10+
  - Docker Compose V2 (included in Docker Desktop)
- **Git** for cloning the repository
- **Make** (optional but recommended)
  - Windows: Install via [chocolatey](https://chocolatey.org/): `choco install make`
  - Mac: Included with Xcode Command Line Tools
  - Linux: `sudo apt install make`

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# At minimum, set OPENAI_API_KEY for LLM functionality
```

### 2. Start Services

```bash
# Start all services
make up

# Or without make:
docker compose -f docker-compose.local.yml up -d
```

### 3. Verify

```bash
# Check health
make health

# Or:
curl http://localhost:8001/health

# Check readiness (dependencies)
make ready

# Or:
curl http://localhost:8001/ready
```

Expected output:
```json
{
  "status": "ok",
  "timestamp": "2024-12-16T...",
  "version": "1.0.0"
}
```

## Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| MAS API | http://localhost:8001 | Main API endpoint |
| MAS Health | http://localhost:8001/health | Liveness check |
| MAS Ready | http://localhost:8001/ready | Readiness check |
| MAS Metrics | http://localhost:8001/metrics | Prometheus metrics |
| LiteLLM Proxy | http://localhost:4000 | LLM API gateway |
| Grafana | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| Prometheus | http://localhost:9090 | Metrics database |
| Qdrant | http://localhost:6333 | Vector database UI |

## Configuration

### Environment Variables

Edit `.env` to configure the system. Key settings:

```bash
# LLM Provider (openai, azure, gemini, anthropic, ollama)
LLM_DEFAULT_PROVIDER=openai

# Your OpenAI API key
OPENAI_API_KEY=sk-your-key-here

# Models for different purposes
LLM_MODEL_PLANNING=gpt-4o           # Complex reasoning
LLM_MODEL_EXECUTION=gpt-4o-mini     # General tasks
LLM_MODEL_FAST=gpt-4o-mini          # Quick responses
LLM_MODEL_EMBEDDING=text-embedding-3-small

# Enable approval gates for risky actions
APPROVAL_REQUIRED=false
```

### Switching LLM Providers

#### Use OpenAI (default)
```bash
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
```

#### Use Azure OpenAI
```bash
LLM_DEFAULT_PROVIDER=azure
AZURE_API_KEY=your-azure-key
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2024-02-15-preview
LLM_MODEL_PLANNING=azure-gpt-4o
```

#### Use Google Gemini
```bash
LLM_DEFAULT_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
LLM_MODEL_PLANNING=gemini-1.5-pro
LLM_MODEL_FAST=gemini-1.5-flash
```

#### Use Local Models (Ollama)
```bash
# Start with local LLM profile
make up-local

# Configure
LLM_DEFAULT_PROVIDER=ollama
LLM_MODEL_PLANNING=llama3.2
LLM_MODEL_FAST=mistral
```

#### Use Anthropic Claude
```bash
LLM_DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
LLM_MODEL_PLANNING=claude-3-5-sonnet
```

## Common Commands

```bash
# Start services
make up

# Start with local LLM (Ollama)
make up-local

# Start with full observability stack
make up-observability

# View logs
make logs                    # All services
make logs s=mas-orchestrator # Specific service

# Stop services
make down

# Stop and remove volumes (DESTROYS DATA)
make down-v

# Reset database
make reset-db

# Open database shell
make db-shell

# Open Redis CLI
make redis-cli

# Run tests
make test

# Format code
make fmt

# Run linters
make lint

# Check available models
make llm-models

# Open Grafana
make grafana-open
```

## Development Workflow

### 1. Making Code Changes

The MAS orchestrator container mounts your local code:
- Changes to `mycosoft_mas/` are reflected immediately (with hot reload in dev mode)
- Changes to config files require a restart: `make restart`

### 2. Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run smoke tests against running services
make test-smoke
```

### 3. Viewing Logs

```bash
# Stream all logs
make logs

# Stream specific service
make logs s=mas-orchestrator

# View in Docker Desktop
# Open Docker Desktop > Containers > mas-orchestrator > Logs
```

### 4. Debugging

1. **Check service status:**
   ```bash
   make ps
   ```

2. **Check health endpoints:**
   ```bash
   make health
   make ready
   ```

3. **View detailed logs:**
   ```bash
   docker compose logs mas-orchestrator --tail=100
   ```

4. **Open shell in container:**
   ```bash
   make shell
   ```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network: mas-network              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐  │
│  │    MAS       │────▶│   LiteLLM    │───▶│   OpenAI/    │  │
│  │ Orchestrator │     │    Proxy     │    │   Gemini/    │  │
│  │  :8001       │     │    :4000     │    │   Ollama     │  │
│  └──────┬───────┘     └──────────────┘    └──────────────┘  │
│         │                                                    │
│         │  ┌──────────────┐                                  │
│         ├─▶│  PostgreSQL  │  (State, Audit Logs)            │
│         │  │    :5432     │                                  │
│         │  └──────────────┘                                  │
│         │                                                    │
│         │  ┌──────────────┐                                  │
│         ├─▶│    Redis     │  (Cache, Queues)                │
│         │  │    :6379     │                                  │
│         │  └──────────────┘                                  │
│         │                                                    │
│         │  ┌──────────────┐                                  │
│         └─▶│   Qdrant     │  (Vector Embeddings)            │
│            │    :6333     │                                  │
│            └──────────────┘                                  │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │  Prometheus  │◀────│   Grafana    │                      │
│  │    :9090     │     │    :3000     │                      │
│  └──────────────┘     └──────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Services won't start

1. Check Docker is running
2. Check port conflicts: `make ps`
3. View logs: `make logs`
4. Ensure `.env` exists and has required keys

### LLM calls failing

1. Verify API key is set in `.env`
2. Check LiteLLM health: `curl http://localhost:4000/health`
3. View LiteLLM logs: `make logs s=litellm`
4. Test model availability: `make llm-models`

### Database connection errors

1. Wait for PostgreSQL to be ready (check `make ready`)
2. Verify credentials in `.env`
3. Try resetting: `make reset-db`

### Out of memory

1. Increase Docker memory limit (Docker Desktop > Settings > Resources)
2. Use smaller models with Ollama
3. Reduce number of running services

### Permission errors (Linux)

```bash
# Fix Docker socket permissions
sudo chmod 666 /var/run/docker.sock

# Or add user to docker group
sudo usermod -aG docker $USER
# Then log out and back in
```

## Next Steps

1. **Explore the API:** Visit http://localhost:8001/docs for Swagger UI
2. **View dashboards:** Open Grafana at http://localhost:3000
3. **Run an agent task:** See [Agent Documentation](./AGENTS.md)
4. **Configure approval gates:** Edit `.env` to enable `APPROVAL_REQUIRED=true`

## Additional Resources

- [API Reference](./API.md)
- [Agent Documentation](./AGENTS.md)
- [Architecture Guide](./ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)
