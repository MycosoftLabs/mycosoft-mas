# Mycosoft MAS Development Guide - Version 0.1

This guide provides detailed information for developers working on the Mycosoft Multi-Agent System.

## Development Environment Setup

### Prerequisites

1. Install required software:
   - Python 3.11
   - Node.js 18+
   - Docker and Docker Compose
   - Poetry for Python dependency management
   - Git

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mycosoft-mas.git
   cd mycosoft-mas
   ```

3. Install Poetry:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

4. Install dependencies:
   ```bash
   poetry install
   ```

## Project Structure

### Core Components

- `mycosoft_mas/`: Core MAS implementation
  - `agents/`: Individual agent implementations
  - `core/`: Core system functionality
  - `services/`: Service implementations
  - `integrations/`: External service integrations

### Frontend

- `app/`: Next.js frontend application
- `components/`: React components
- `styles/`: CSS and styling files
- `public/`: Static assets

### Configuration

- `config/`: Configuration files
- `docker/`: Docker configuration
- `grafana/`: Monitoring configuration
- `prometheus/`: Metrics configuration

## Development Workflow

1. **Branch Management**
   - Main branch: `main`
   - Feature branches: `feature/feature-name`
   - Bug fixes: `fix/bug-name`

2. **Adding Dependencies**
   ```bash
   # Python dependencies
   poetry add package-name
   poetry lock

   # Rebuild affected services
   docker-compose build service-name
   docker-compose up -d
   ```

3. **Running Tests**
   ```bash
   poetry run pytest
   ```

4. **Code Style**
   - Python: Black formatter
   - TypeScript: Prettier
   - Pre-commit hooks available

## Service Architecture

### Core Services

1. **MAS Orchestrator**
   - Port: 8001
   - Main API endpoint
   - Coordinates other services

2. **Agent Manager**
   - Manages agent lifecycle
   - Handles agent communication

3. **Task Manager**
   - Manages task distribution
   - Handles task scheduling

4. **Integration Manager**
   - Manages external integrations
   - Handles API connections

### Support Services

1. **Redis**
   - Port: 6379
   - Used for caching and message queuing

2. **PostgreSQL**
   - Port: 5432
   - Primary database

3. **Prometheus**
   - Port: 9090
   - Metrics collection

4. **Grafana**
   - Port: 3002
   - Monitoring dashboards

## Configuration Files

### .env
```env
MAS_ENV=development
DEBUG_MODE=true
LOG_LEVEL=DEBUG
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://mas:mas@db:5432/mas
```

### docker-compose.yml
- Service definitions
- Network configuration
- Volume mappings

### config.yaml
- Application configuration
- Agent settings
- Integration parameters

## Monitoring

1. **Health Checks**
   - Each service implements `/health` endpoint
   - Regular status monitoring

2. **Metrics**
   - Prometheus metrics at `/metrics`
   - Custom Grafana dashboards

3. **Logging**
   - Structured logging
   - Log aggregation in `logs/` directory

## Important Notes

1. Version 0.1 is the current stable release
2. All changes require approval from Morgan Rockwell
3. Configuration files are version controlled
4. Use Poetry for dependency management
5. Follow the established code style guidelines

## Support

For any questions or issues:
1. Check existing documentation
2. Contact the development team
3. Raise issues through the appropriate channels

## License

Proprietary - All rights reserved. © Morgan Rockwell 