# NLM - Nature Learning Model

**The world's first multi-modal foundation model that learns the information-bearing signals of living Earth systems and translates them into operational representations for humans, machines, and scientific workflows.**

## Overview

NLM (Nature Learning Model) is a revolutionary multi-modal foundation model designed to understand and interpret the complex information-bearing signals of living Earth systems. It processes diverse data modalities including environmental sensors, biological observations, geospatial data, temporal patterns, and scientific literature to create operational representations that bridge the gap between natural systems and computational workflows.

## Key Features

### Multi-Modal Learning
- **Environmental Data**: Temperature, humidity, CO2, air quality, radiation, magnetic fields
- **Biological Signals**: Species observations, growth patterns, genetic sequences, ecological interactions
- **Geospatial Intelligence**: Location-based patterns, terrain analysis, climate zones
- **Temporal Dynamics**: Time-series analysis, seasonal patterns, predictive modeling
- **Scientific Literature**: Research paper analysis, knowledge extraction, citation networks

### Operational Representations
- **Structured Knowledge Graphs**: Entity-relationship models of natural systems
- **Predictive Models**: Forecasting environmental and biological outcomes
- **Anomaly Detection**: Identifying unusual patterns in Earth systems
- **Recommendation Systems**: Suggesting optimal actions based on learned patterns
- **Scientific Workflows**: Automated hypothesis generation and testing

### Integration Capabilities
- **NatureOS**: Real-time sensor data ingestion and device management
- **MINDEX**: Mycological database integration for species knowledge
- **MAS (Multi-Agent System)**: Agent-based orchestration and decision-making
- **Website API**: Public-facing interfaces and documentation
- **Database Systems**: PostgreSQL, Qdrant vector store, Redis caching

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    NLM Core Engine                          │
├─────────────────────────────────────────────────────────────┤
│  Multi-Modal Encoders  │  Attention Mechanisms  │  Decoders │
│  - Environmental       │  - Cross-modal         │  - Text   │
│  - Biological          │  - Temporal            │  - Graphs │
│  - Geospatial          │  - Spatial             │  - Actions│
│  - Temporal            │                        │           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐  ┌─────────▼─────────┐  ┌─────▼──────┐
│  Knowledge   │  │  Prediction       │  │  Action   │
│  Graph       │  │  Engine           │  │  Generator │
└───────┬──────┘  └─────────┬─────────┘  └─────┬──────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐  ┌─────────▼─────────┐  ┌─────▼──────┐
│  NatureOS    │  │  MINDEX           │  │  MAS       │
│  Integration │  │  Integration      │  │  Integration│
└──────────────┘  └───────────────────┘  └────────────┘
```

### Data Flow

1. **Ingestion**: Multi-modal data streams from NatureOS devices, MINDEX database, and external APIs
2. **Encoding**: Raw data transformed into unified embedding space
3. **Learning**: Attention mechanisms identify patterns and relationships
4. **Representation**: Knowledge graphs and operational models generated
5. **Application**: Predictions, recommendations, and actions delivered to users and systems

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (with PostGIS extension)
- Redis 7+
- Qdrant vector database
- CUDA-capable GPU (recommended for training)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/MycosoftLabs/NLM.git
cd NLM

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and API credentials

# Initialize database
python scripts/init_database.py

# Run migrations
alembic upgrade head

# Start the API server
uvicorn nlm.api.main:app --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nlm
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# NatureOS Integration
NATUREOS_API_URL=http://localhost:8002
NATUREOS_API_KEY=your_api_key
NATUREOS_TENANT_ID=your_tenant_id

# MINDEX Integration
MINDEX_DATABASE_URL=postgresql://user:pass@localhost:5432/mindex
MINDEX_API_URL=http://localhost:8003
MINDEX_API_KEY=your_api_key

# MAS Integration
MAS_API_URL=http://localhost:8001
MAS_API_KEY=your_api_key

# Website Integration
WEBSITE_API_URL=https://mycosoft.vercel.app/api
WEBSITE_API_KEY=your_api_key

# Model Configuration
NLM_MODEL_PATH=./models/nlm-base-v1
NLM_DEVICE=cuda  # or cpu
NLM_BATCH_SIZE=32
NLM_MAX_SEQUENCE_LENGTH=4096
```

## Usage

### Python API

```python
from nlm import NLMClient

# Initialize client
client = NLMClient(
    database_url="postgresql://...",
    natureos_api_url="http://localhost:8002",
    mindex_api_url="http://localhost:8003"
)

# Process environmental data
result = await client.process_environmental_data(
    temperature=22.5,
    humidity=65.0,
    co2=420,
    location={"lat": 45.5, "lon": -122.6},
    timestamp="2024-01-15T10:30:00Z"
)

# Query knowledge graph
knowledge = await client.query_knowledge_graph(
    query="What species thrive in temperate rainforests?",
    context={"location": "Pacific Northwest"}
)

# Generate predictions
prediction = await client.predict(
    entity_type="species_growth",
    entity_id="pleurotus_ostreatus",
    time_horizon="30d",
    conditions={"temperature_range": [18, 24], "humidity_range": [60, 80]}
)

# Get recommendations
recommendations = await client.recommend(
    scenario="optimal_growth_conditions",
    constraints={"location": "indoor", "species": "shiitake"}
)
```

### REST API

```bash
# Process data
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "environmental",
    "data": {
      "temperature": 22.5,
      "humidity": 65.0,
      "co2": 420
    },
    "location": {"lat": 45.5, "lon": -122.6}
  }'

# Query knowledge graph
curl -X POST http://localhost:8000/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What environmental conditions favor Pleurotus ostreatus?",
    "context": {"location": "temperate"}
  }'

# Get predictions
curl -X GET "http://localhost:8000/api/v1/predict/species_growth/pleurotus_ostreatus?horizon=30d"
```

## Database Schema

NLM uses PostgreSQL with the following key schemas:

### `nlm.models`
Stores trained model artifacts and metadata.

### `nlm.knowledge_graph`
Entity-relationship knowledge graph of natural systems.

### `nlm.predictions`
Historical and real-time predictions.

### `nlm.integrations`
Integration state and synchronization metadata.

See [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) for complete schema documentation.

## Integrations

### NatureOS Integration

NLM integrates with NatureOS to:
- Ingest real-time sensor data from IoT devices
- Process environmental monitoring streams
- Correlate device telemetry with biological outcomes
- Generate device-specific recommendations

```python
from nlm.integrations.natureos import NatureOSIngester

ingester = NatureOSIngester(
    natureos_api_url="http://localhost:8002",
    nlm_client=client
)

# Start ingesting data from all devices
await ingester.start_ingestion()

# Process data from specific device
await ingester.process_device_data(device_id="mycobrain-001")
```

### MINDEX Integration

NLM integrates with MINDEX to:
- Access mycological species database
- Learn from historical observations
- Enhance predictions with taxonomic knowledge
- Generate species-specific insights

```python
from nlm.integrations.mindex import MINDEXConnector

connector = MINDEXConnector(
    mindex_api_url="http://localhost:8003",
    nlm_client=client
)

# Sync species data
await connector.sync_species_data()

# Query species with NLM context
species = await connector.query_species_with_nlm(
    query="temperate forest species",
    nlm_context={"location": "Pacific Northwest"}
)
```

### MAS Integration

NLM integrates with the Multi-Agent System to:
- Provide intelligent decision support to agents
- Generate action recommendations
- Process agent queries with natural language understanding
- Maintain shared knowledge state

```python
from nlm.integrations.mas import MASConnector

connector = MASConnector(
    mas_api_url="http://localhost:8001",
    nlm_client=client
)

# Register NLM as a service
await connector.register_service()

# Process agent query
response = await connector.process_agent_query(
    agent_id="mycology_agent",
    query="What are optimal conditions for growing shiitake?",
    context={"current_conditions": {...}}
)
```

### Website Integration

NLM provides public API endpoints for the website:
- Model inference endpoints
- Knowledge graph queries
- Prediction services
- Documentation and examples

See [WEBSITE_INTEGRATION.md](./WEBSITE_INTEGRATION.md) for details.

## Development

### Project Structure

```
NLM/
├── nlm/
│   ├── core/              # Core model architecture
│   ├── encoders/          # Multi-modal encoders
│   ├── decoders/          # Output decoders
│   ├── knowledge/         # Knowledge graph management
│   ├── predictions/       # Prediction engine
│   ├── api/               # REST API
│   └── integrations/      # External system integrations
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── migrations/            # Database migrations
├── docs/                  # Documentation
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nlm --cov-report=html

# Run specific test suite
pytest tests/test_integrations.py
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](./LICENSE) file for details.

## Support

- **Documentation**: [https://github.com/MycosoftLabs/NLM/docs](https://github.com/MycosoftLabs/NLM/docs)
- **Issues**: [https://github.com/MycosoftLabs/NLM/issues](https://github.com/MycosoftLabs/NLM/issues)
- **Email**: support@mycosoft.com

## Citation

If you use NLM in your research, please cite:

```bibtex
@software{nlm2024,
  title={NLM: Nature Learning Model},
  author={Mycosoft Labs},
  year={2024},
  url={https://github.com/MycosoftLabs/NLM}
}
```

