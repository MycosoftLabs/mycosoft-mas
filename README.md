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

# Mycosoft MAS (Multi-Agent System) - Version 0.1

A sophisticated multi-agent system designed for managing and coordinating various aspects of mycological research and operations.

## Overview

Mycosoft MAS is a comprehensive platform that integrates multiple intelligent agents to handle various tasks related to mycological research, data management, and operational coordination. The system is built with modern technologies and follows best practices in software development.

## Key Features

- 🤖 Multi-agent coordination system
- 📊 Real-time monitoring and metrics
- 🔄 Automated task management
- 🔐 Secure communication protocols
- 📈 Data analytics and visualization
- 🌐 Web-based user interface
- 🔌 Extensible plugin architecture

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mycosoft-mas.git
   cd mycosoft-mas
   ```

2. **Set up environment**
   ```bash
   # Copy environment file
   cp .env.example .env

   # Install Python dependencies
   poetry install

   # Install Node.js dependencies
   npm install
   ```

3. **Start services**
   ```bash
   # Start all services
   docker-compose up -d
   ```

4. **Access the application**
   - Web Interface: http://localhost:3000
   - Grafana Dashboard: http://localhost:3002
   - Prometheus: http://localhost:9090

## Technology Stack

- **Backend**
  - Python 3.11
  - FastAPI
  - PostgreSQL
  - Redis
  - Celery

- **Frontend**
  - Next.js 14
  - React
  - TypeScript
  - Tailwind CSS
  - Shadcn UI

- **Monitoring**
  - Prometheus
  - Grafana
  - Custom metrics

- **Infrastructure**
  - Docker
  - Docker Compose
  - Poetry
  - Node.js

## Documentation

- [Development Guide](docs/development.md)
- [API Documentation](docs/api.md)
- [Agent Documentation](docs/agents/README.md)
- [Service Documentation](docs/services/README.md)

## Project Structure

```
mycosoft-mas/
├── agents/           # Agent implementations
├── app/             # Next.js frontend
├── components/      # React components
├── config/          # Configuration files
├── data/           # Data storage
├── docker/         # Docker configurations
├── docs/           # Documentation
├── grafana/        # Monitoring dashboards
├── mycosoft_mas/   # Core backend
├── prometheus/     # Metrics configuration
└── tests/          # Test suites
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved. © Morgan Rockwell

## Support

For support and inquiries, please contact the development team or refer to the documentation.

## Acknowledgments

Special thanks to all contributors and stakeholders who have made this project possible.
