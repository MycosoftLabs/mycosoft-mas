# mycocomp Development Environment Setup

This guide configures mycocomp (your primary development workstation with RTX 5090) as the isolated development environment for MYCA.

## System Specifications

| Component | Specification |
|-----------|---------------|
| **Role** | Development, Testing, AI Experimentation |
| **GPU** | NVIDIA RTX 5090 (24GB VRAM) |
| **OS** | Windows 10/11 |
| **Network** | 192.168.0.x (same network as production) |
| **Storage** | NFS/SMB mount to UDM Pro 26TB |

## Prerequisites

1. **NVIDIA Drivers**: Latest Game Ready or Studio driver
2. **Docker Desktop**: With WSL2 backend and GPU support
3. **NVIDIA Container Toolkit**: For GPU passthrough in containers
4. **Git**: For version control
5. **Python 3.11+**: For local development
6. **Node.js 20+**: For frontend development

## Step 1: Install Docker Desktop with GPU Support

1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Enable WSL2 backend in Docker Desktop settings
3. Enable GPU support:
   - Settings → Resources → WSL Integration → Enable for your distro
   - Settings → Docker Engine → Add:
   ```json
   {
     "features": {
       "buildkit": true
     },
     "runtimes": {
       "nvidia": {
         "path": "nvidia-container-runtime",
         "runtimeArgs": []
       }
     }
   }
   ```

## Step 2: Mount NAS Storage

Run the mount script:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\mount_nas.ps1
```

This will:
- Mount UDM Pro storage as M: drive
- Create directory structure if missing
- Set NAS_STORAGE_PATH environment variable

## Step 3: Configure Environment

Copy the development environment configuration:

```powershell
# Copy development config
Copy-Item config\development.env .env.local
```

Edit `.env.local` and add your API keys:

```bash
# Required API keys
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
ELEVENLABS_API_KEY=your-key
```

## Step 4: Start Development Stack

Use the development docker-compose configuration:

```powershell
# Start all development services
docker compose -f docker-compose.yml up -d

# Or start specific services
docker compose -f docker-compose.yml up -d postgres redis qdrant ollama
```

## Step 5: Initialize Ollama Models

Pull required LLM models (runs on RTX 5090):

```powershell
# Pull models
docker exec -it ollama ollama pull llama3.1
docker exec -it ollama ollama pull codellama
docker exec -it ollama ollama pull mistral

# Verify GPU usage
docker exec -it ollama nvidia-smi
```

## Step 6: Verify Setup

Run the verification script:

```powershell
.\scripts\verify_storage.ps1
```

Test the development stack:

```powershell
# Health check
curl http://localhost:8001/health

# Test Ollama
curl http://localhost:11434/api/tags

# Test Whisper
curl http://localhost:8765/health
```

## Development Workflow

### Running MYCA Locally

```powershell
# Start the full stack
docker compose up -d

# View logs
docker compose logs -f mas-orchestrator

# Rebuild after code changes
docker compose up -d --build mas-orchestrator
```

### Running Python Directly (for debugging)

```powershell
# Activate virtual environment
.\venv311\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run orchestrator directly
python -m uvicorn mycosoft_mas.core.main:app --reload --port 8001
```

### Frontend Development

```powershell
# Navigate to dashboard
cd unifi-dashboard

# Install dependencies
npm install

# Start dev server
npm run dev
```

## GPU Workloads

The RTX 5090 is used for:

1. **Ollama LLMs**: Local inference for agent reasoning
2. **Whisper**: Real-time speech-to-text
3. **Vector Embeddings**: Generating embeddings for Qdrant
4. **NLM Training**: Fine-tuning Nature Learning Model

### Monitoring GPU Usage

```powershell
# Check GPU status
nvidia-smi

# Watch GPU usage
nvidia-smi -l 1

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| MAS Orchestrator | 8001 | Main API |
| PostgreSQL | 5433 | Database |
| Redis | 6390 | Cache |
| Qdrant | 6345 | Vector DB |
| Ollama | 11434 | LLM API |
| Whisper | 8765 | STT API |
| N8N | 5678 | Workflows |
| TTS | 5500 | Text-to-speech |
| Dashboard | 3100 | Web UI |
| Voice UI | 8090 | Voice interface |

## Environment Separation

mycocomp is **isolated** from production:

- Uses local databases (not production)
- Can read shared data from NAS
- Cannot modify production MYCA directly
- Deploys to production via CI/CD pipeline

## Troubleshooting

### GPU Not Detected in Docker

```powershell
# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi

# If fails, reinstall NVIDIA Container Toolkit
# See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
```

### NAS Mount Failed

```powershell
# Check connectivity
Test-NetConnection -ComputerName 192.168.0.1 -Port 445

# Remount with force
.\scripts\mount_nas.ps1 -Force
```

### Ollama Out of Memory

```powershell
# Use smaller models
docker exec -it ollama ollama run llama3.1:8b

# Or adjust VRAM allocation in Ollama
```

## Next Steps

After setup:

1. Test local MYCA development
2. Run agent tests with GPU acceleration
3. Develop new features locally
4. Push to Git and deploy to production via CI/CD
