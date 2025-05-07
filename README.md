# ENVINT Platform

The ENVINT (Environmental Intelligence) Platform is a comprehensive system for monitoring and analyzing environmental data using ESP32 devices, with a focus on mycelium and bioremediation applications.

## Features

- **Multi-Device Management**: Coordinate multiple ESP32 devices through a Raspberry Pi Zero
- **Sensor Data Processing**: Real-time processing of environmental and bioelectric signals
- **Oyster Mushroom Monitoring**: Specialized monitoring for oyster mushroom cultivation
- **Bioremediation Analysis**: Advanced analysis of bioremediation processes
- **Mycelium Analysis**: Neural network-based analysis of mycelium signals
- **Memory Storage**: Integration with Mem0.ai for persistent data storage
- **REST API**: FastAPI-based interface for system interaction

## Prerequisites

- Python 3.8 or higher
- ESP32 devices with appropriate sensors
- Raspberry Pi Zero (optional, for device coordination)
- Azure IoT Hub account
- Mem0.ai API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/envint-platform.git
cd envint-platform
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
AZURE_IOT_HUB_CONNECTION_STRING=your_connection_string
MEM0_API_KEY=your_api_key
```

## Usage

1. Start the ENVINT platform:
```bash
python main.py
```

2. The API will be available at `http://localhost:8000`

3. Access the API documentation at `http://localhost:8000/docs`

## API Endpoints

### Health Check
- `GET /health`: Check system health

### Device Management
- `GET /devices`: List all registered devices
- `POST /devices/register`: Register a new device
- `DELETE /devices/{device_id}`: Unregister a device
- `GET /devices/{device_id}/status`: Get device status
- `PUT /devices/{device_id}/config`: Update device configuration

### Sensor Data
- `POST /sensor/data`: Process incoming sensor data
- `GET /sensor/data/{device_id}`: Get historical sensor data

### Oyster Monitor
- `POST /oyster/data`: Process oyster monitor data
- `GET /oyster/data`: Get historical oyster monitor data
- `PUT /oyster/config`: Update oyster monitor configuration

### Bioremediation
- `POST /bioremediation/analyze`: Analyze bioremediation data
- `GET /bioremediation/recommendations`: Get bioremediation recommendations

### Mycelium Analysis
- `POST /mycelium/analyze`: Analyze mycelium signals
- `GET /mycelium/interpretations`: Get mycelium signal interpretations

### Memory Operations
- `POST /memory/store`: Store data in Mem0.ai
- `GET /memory/retrieve`: Retrieve data from Mem0.ai

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ESP32 Arduino Core
- Azure IoT Hub
- CrewAI Framework
- LangChain
- TensorFlow
- PyTorch

# Mycosoft Multi-Agent System (MAS)

A distributed multi-agent system for intelligent task processing and orchestration.

## Features

- Distributed agent architecture
- Redis-based message queue
- PostgreSQL database
- Qdrant vector database
- Prometheus monitoring
- Grafana dashboards

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- Python 3.11+
- Poetry

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mycosoft/mas.git
cd mas
```

2. Install dependencies:
```bash
poetry install
```

3. Start the services:
```bash
docker compose -f docker-compose.prod.yml up -d
```

### Accessing Services

- Orchestrator API: http://localhost:8001
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Qdrant: http://localhost:6333

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Style

```bash
poetry run black .
poetry run isort .
poetry run mypy .
poetry run pylint .
```

## License

MIT
