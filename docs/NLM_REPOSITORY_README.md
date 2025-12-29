# NLM - Nature Learning Model

**The world's first multi-modal foundation model that learns the information-bearing signals of living Earth systems and translates them into operational representations for humans, machines, and scientific workflows.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

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

## Quick Start

### Installation

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

# Start the API server
uvicorn nlm.api.main:app --host 0.0.0.0 --port 8000
```

### Basic Usage

```python
from nlm import NLMClient

# Initialize client
client = NLMClient(
    database_url="postgresql://...",
    natureos_api_url="http://localhost:8002"
)

# Process environmental data
result = await client.process_environmental_data(
    temperature=22.5,
    humidity=65.0,
    co2=420,
    location={"lat": 45.5, "lon": -122.6}
)

# Query knowledge graph
knowledge = await client.query_knowledge_graph(
    query="What species thrive in temperate rainforests?"
)

# Generate predictions
prediction = await client.predict(
    entity_type="species_growth",
    entity_id="pleurotus_ostreatus",
    time_horizon="30d"
)
```

## Documentation

- **[Full Documentation](./docs/NLM_README.md)**: Comprehensive guide
- **[Database Schema](./docs/NLM_DATABASE_SCHEMA.md)**: Database structure
- **[Integration Guide](../docs/INTEGRATION_GUIDE.md)**: Integration with other systems
- **[Platform Structure](../docs/PLATFORM_STRUCTURE_PLAN.md)**: Overall platform architecture

## Architecture

NLM consists of:

- **Multi-Modal Encoders**: Process diverse input modalities
- **Attention Mechanisms**: Cross-modal, temporal, and spatial attention
- **Knowledge Graph**: Entity-relationship knowledge storage
- **Prediction Engine**: Generate predictions and recommendations
- **Integration Layer**: Connect with NatureOS, MINDEX, MAS, and Website

See [docs/NLM_README.md](./docs/NLM_README.md) for detailed architecture.

## Integrations

### NatureOS

Ingest real-time sensor data from IoT devices:

```python
from nlm.integrations.natureos import NatureOSIngester

ingester = NatureOSIngester(natureos_api_url="...", nlm_client=client)
await ingester.start_ingestion()
```

### MINDEX

Access mycological species database:

```python
from nlm.integrations.mindex import MINDEXConnector

connector = MINDEXConnector(mindex_api_url="...", nlm_client=client)
await connector.sync_species_data()
```

### MAS

Provide intelligent decision support to agents:

```python
from nlm.integrations.mas import MASConnector

connector = MASConnector(mas_api_url="...", nlm_client=client)
await connector.register_service()
```

## API Reference

### REST API

- `POST /api/v1/process` - Process multi-modal data
- `POST /api/v1/knowledge/query` - Query knowledge graph
- `GET /api/v1/predict/{type}/{id}` - Generate predictions
- `POST /api/v1/recommend` - Get recommendations
- `GET /api/v1/health` - Health check

See [API Documentation](./docs/API.md) for complete reference.

## Development

### Project Structure

```
NLM/
├── nlm/                    # Core package
│   ├── core/               # Model architecture
│   ├── encoders/           # Multi-modal encoders
│   ├── decoders/           # Output decoders
│   ├── knowledge/          # Knowledge graph
│   ├── predictions/        # Prediction engine
│   ├── api/                # REST API
│   └── integrations/       # External integrations
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── migrations/             # Database migrations
└── docs/                   # Documentation
```

### Running Tests

```bash
pytest
pytest --cov=nlm --cov-report=html
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](./LICENSE) file for details.

## Support

- **Documentation**: [docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/MycosoftLabs/NLM/issues)
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

