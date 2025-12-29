# Mycosoft Platform Structure Plan

This document outlines the complete structure and architecture of the Mycosoft platform, including NLM, SDK, NatureOS, Website, MAS, and their integrations.

## Platform Overview

The Mycosoft platform consists of:

1. **NLM (Nature Learning Model)**: Multi-modal foundation model
2. **SDK (NatureOS Developer SDK)**: Client library for NatureOS
3. **NatureOS**: Cloud IoT platform for environmental monitoring
4. **Website**: Public-facing Next.js application
5. **MAS (Multi-Agent System)**: Agent orchestration platform
6. **MINDEX**: Mycological Index Database
7. **MycoBrain**: IoT devices for mushroom cultivation monitoring

## Repository Structure

```
MycosoftLabs/
├── NLM/                    # Nature Learning Model
│   ├── nlm/                # Core Python package
│   ├── api/                 # REST API
│   ├── integrations/       # Integration modules
│   ├── migrations/         # Database migrations
│   ├── tests/              # Test suite
│   ├── docs/               # Documentation
│   ├── README.md           # Main README
│   └── requirements.txt    # Dependencies
│
├── sdk/                    # NatureOS Developer SDK
│   ├── natureos_sdk/       # Python package
│   ├── @mycosoft/          # TypeScript package
│   ├── examples/           # Code examples
│   ├── tests/              # Test suite
│   ├── docs/               # Documentation
│   ├── README.md           # Main README
│   └── package.json        # Node.js dependencies
│
├── NatureOS/               # Cloud IoT Platform
│   ├── api/                # REST API server
│   ├── device-manager/     # Device management service
│   ├── data-processor/     # Data processing service
│   ├── database/           # Database schemas
│   ├── docs/               # Documentation
│   └── README.md           # Main README
│
├── mycosoft-mas/           # Multi-Agent System (this repo)
│   ├── mycosoft_mas/       # Core Python package
│   ├── agents/             # Agent implementations
│   ├── integrations/       # Integration clients
│   ├── app/                # Next.js UI
│   ├── docker/            # Docker configurations
│   ├── docs/               # Documentation
│   └── README.md           # Main README
│
├── MINDEX/                 # Mycological Index Database
│   ├── api/                # REST API
│   ├── database/           # Database schemas
│   ├── migrations/         # Database migrations
│   ├── docs/               # Documentation
│   └── README.md           # Main README
│
└── website/                # Public Website (in mycosoft-mas/WEBSITE)
    ├── app/                # Next.js app directory
    ├── components/         # React components
    ├── lib/                # Utilities
    ├── public/             # Static assets
    └── README.md           # Main README
```

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Mycosoft Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │   Website     │  Public-facing Next.js application       │
│  │  (Next.js)    │  - Documentation                         │
│  └──────┬────────┘  - Product pages                         │
│         │            - API documentation                     │
│         │            - Integration examples                   │
│         │                                                    │
│         ├──────────────┐                                    │
│         │              │                                    │
│  ┌──────▼──────┐  ┌────▼──────┐                            │
│  │     NLM     │  │    SDK    │                            │
│  │  (Model)    │  │ (Library) │                            │
│  └──────┬──────┘  └────┬──────┘                            │
│         │              │                                    │
│         │              │                                    │
│  ┌──────▼──────────────▼──────┐                            │
│  │         NatureOS            │                            │
│  │      (Cloud Platform)       │                            │
│  └──────┬──────────────────────┘                            │
│         │                                                    │
│  ┌──────▼──────┐                                            │
│  │     MAS     │  Multi-Agent System                        │
│  │(Orchestrator)│  - Agent management                       │
│  └──────┬──────┘  - Task coordination                       │
│         │          - Integration hub                         │
│         │                                                    │
│  ┌──────▼──────┐  ┌──────────────┐                          │
│  │   MINDEX    │  │  MycoBrain   │                          │
│  │  (Database) │  │   (Devices)  │                          │
│  └─────────────┘  └──────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

### 1. Device Data Flow

```
MycoBrain Device
    │
    │ (MQTT/HTTP)
    ▼
NatureOS API
    │
    ├──► SDK (Client Access)
    │
    ├──► NLM (Data Ingestion)
    │    │
    │    └──► Knowledge Graph Update
    │
    └──► MAS (Agent Processing)
         │
         └──► Agent Actions
```

### 2. Query Flow

```
Website User / MAS Agent
    │
    │ (HTTP Request)
    ▼
Website API / MAS API
    │
    ├──► SDK (NatureOS Query)
    │
    ├──► NLM (Knowledge Query)
    │    │
    │    └──► Knowledge Graph Search
    │
    └──► MINDEX (Species Query)
```

### 3. Prediction Flow

```
MAS Agent / Website
    │
    │ (Query)
    ▼
NLM API
    │
    ├──► Process Input Data
    │
    ├──► Query Knowledge Graph
    │
    ├──► Generate Prediction
    │
    └──► Return Results
```

## Database Architecture

### Shared Databases

1. **PostgreSQL (Primary)**
   - MAS: `mas`, `agents`, `tasks`, `knowledge` schemas
   - NLM: `nlm.core`, `nlm.knowledge`, `nlm.predictions`, `nlm.integrations` schemas
   - SDK: `sdk.cache`, `sdk.state`, `sdk.analytics` schemas
   - MINDEX: `mindex.species`, `mindex.observations` schemas
   - NatureOS: `natureos.devices`, `natureos.sensors`, `natureos.data` schemas

2. **Redis (Caching)**
   - Session storage
   - API response caching
   - Real-time data streams

3. **Qdrant (Vector Store)**
   - NLM embeddings
   - Semantic search
   - Similarity matching

### Database Connections

```
┌─────────────────────────────────────────┐
│         PostgreSQL Cluster              │
├─────────────────────────────────────────┤
│  MAS Schema      │  NLM Schema          │
│  SDK Schema      │  MINDEX Schema       │
│  NatureOS Schema │                      │
└─────────────────────────────────────────┘
         │
         ├──► Redis (Cache)
         │
         └──► Qdrant (Vectors)
```

## API Architecture

### API Endpoints

1. **NLM API** (`http://nlm-api:8000`)
   - `/api/v1/process` - Process multi-modal data
   - `/api/v1/knowledge/query` - Query knowledge graph
   - `/api/v1/predict` - Generate predictions
   - `/api/v1/recommend` - Get recommendations
   - `/api/v1/integrations/*` - Integration endpoints

2. **SDK API** (via NatureOS)
   - Device management
   - Sensor data access
   - Command execution

3. **NatureOS API** (`http://natureos-api:8002`)
   - `/devices/*` - Device management
   - `/sensor-data/*` - Sensor data
   - `/commands/*` - Device commands
   - `/health` - Health check

4. **MAS API** (`http://mas-api:8001`)
   - `/agents/*` - Agent management
   - `/tasks/*` - Task management
   - `/integrations/*` - Integration endpoints
   - `/health` - Health check

5. **Website API** (`https://mycosoft.vercel.app/api`)
   - `/api/nlm/*` - NLM proxy endpoints
   - `/api/natureos/*` - NatureOS proxy endpoints
   - `/api/docs/*` - Documentation endpoints

## Integration Patterns

### 1. Direct Integration

Components communicate directly via HTTP/REST APIs.

```
Component A ──HTTP──► Component B
```

### 2. SDK Integration

Components use SDK libraries for type-safe access.

```
Component A ──SDK──► Component B
```

### 3. Database Integration

Components share database schemas for data access.

```
Component A ──Database──► Component B
```

### 4. Event-Driven Integration

Components communicate via events/messages.

```
Component A ──Event──► Message Queue ──Event──► Component B
```

## Deployment Architecture

### Development

```
Local Development
├── Docker Compose
│   ├── PostgreSQL
│   ├── Redis
│   ├── Qdrant
│   ├── MAS API
│   └── Website (Next.js)
│
└── Local Services
    ├── NLM API (Python)
    ├── NatureOS API (Python)
    └── SDK (Library)
```

### Production

```
Production Deployment
├── Cloud Infrastructure
│   ├── Kubernetes Cluster
│   │   ├── NLM Service
│   │   ├── NatureOS Service
│   │   ├── MAS Service
│   │   └── MINDEX Service
│   │
│   ├── Managed Databases
│   │   ├── PostgreSQL (RDS/Cloud SQL)
│   │   ├── Redis (ElastiCache)
│   │   └── Qdrant (Managed)
│   │
│   └── CDN/Edge
│       └── Website (Vercel)
│
└── IoT Devices
    └── MycoBrain Devices
```

## Security Architecture

### Authentication & Authorization

1. **API Keys**: Service-to-service authentication
2. **JWT Tokens**: User authentication (Auth0)
3. **OAuth 2.0**: Third-party integrations
4. **Tenant Isolation**: Multi-tenant support

### Data Security

1. **Encryption**: TLS/SSL for all communications
2. **Secrets Management**: Environment variables, Vault
3. **Access Control**: Role-based access control (RBAC)
4. **Audit Logging**: All operations logged

## Monitoring & Observability

### Metrics

- Prometheus for metrics collection
- Grafana for visualization
- Custom dashboards per component

### Logging

- Structured JSON logging
- Centralized log aggregation
- Correlation IDs for tracing

### Health Checks

- `/health` endpoints on all services
- `/ready` endpoints for readiness checks
- Automated health monitoring

## Development Workflow

### 1. Local Development

```bash
# Start infrastructure
docker compose up -d

# Run services locally
# NLM
cd NLM && uvicorn nlm.api.main:app --reload

# MAS
cd mycosoft-mas && uvicorn mycosoft_mas.core.myca_main:app --reload

# Website
cd website && npm run dev
```

### 2. Testing

```bash
# Unit tests
pytest

# Integration tests
pytest tests/integration

# E2E tests
pytest tests/e2e
```

### 3. Deployment

```bash
# Build and push images
docker build -t mycosoft/nlm:latest ./NLM
docker push mycosoft/nlm:latest

# Deploy to Kubernetes
kubectl apply -f k8s/nlm-deployment.yaml
```

## Documentation Structure

Each repository should include:

1. **README.md**: Overview, quick start, basic usage
2. **docs/API.md**: API reference documentation
3. **docs/INTEGRATION.md**: Integration guides
4. **docs/DATABASE.md**: Database schema documentation
5. **docs/DEPLOYMENT.md**: Deployment guides
6. **docs/CONTRIBUTING.md**: Contribution guidelines

## Future Enhancements

1. **GraphQL API**: Unified GraphQL endpoint
2. **WebSocket Support**: Real-time data streaming
3. **gRPC**: High-performance RPC for internal services
4. **Service Mesh**: Istio/Linkerd for service communication
5. **Event Sourcing**: Event-driven architecture
6. **CQRS**: Command Query Responsibility Segregation

## Conclusion

This platform structure provides a scalable, maintainable architecture for the Mycosoft ecosystem. Each component is designed to be independently deployable while maintaining strong integration capabilities.

