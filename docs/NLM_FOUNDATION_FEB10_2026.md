# Nature Learning Model (NLM) Foundation

**Date:** February 10, 2026  
**Status:** Foundation Complete  
**Author:** Mycosoft MAS Team

## Overview

The Nature Learning Model (NLM) is a domain-specific language model designed for mycology and natural sciences. It is part of the Mycosoft Multi-Agent System (MAS) and provides expert knowledge about fungi, taxonomy, ecology, and environmental sciences.

## Architecture

```
mycosoft_mas/nlm/
├── __init__.py           # Module exports and documentation
├── config.py             # Configuration classes
├── memory_store.py       # Memory integration (existing)
├── data_pipeline.py      # Legacy data pipeline (existing)
├── trainer.py            # Legacy trainer (existing)
├── inference.py          # Legacy inference (existing)
├── models/
│   ├── __init__.py       # Model exports
│   └── base_model.py     # NLMBaseModel, NLMEmbeddingModel
├── training/
│   ├── __init__.py       # Training exports
│   └── trainer.py        # NLMTrainer, DataCollator, TrainingMetrics
├── inference/
│   ├── __init__.py       # Inference exports
│   └── service.py        # NLMService, PredictionRequest, PredictionResult
└── datasets/
    ├── __init__.py       # Dataset exports
    └── loaders.py        # NLMDataLoader, DataProcessor, MINDEXConnector
```

## Components

### 1. Configuration (`config.py`)

The `NLMConfig` class provides comprehensive configuration for:

- **Model Architecture:** Base model, LoRA settings, hidden dimensions
- **Training:** Learning rate, batch size, epochs, optimizer settings
- **Data:** Training data paths, categories, quality filters
- **Inference:** Device settings, generation defaults, fallback options

```python
from mycosoft_mas.nlm import get_nlm_config

config = get_nlm_config()
print(f"Model: {config.model_name} v{config.model_version}")
print(f"Base: {config.architecture.base_model}")
```

Environment variable overrides are supported:
- `NLM_MODEL_DIR` - Model weights directory
- `NLM_LEARNING_RATE` - Training learning rate
- `NLM_BATCH_SIZE` - Training batch size
- `NLM_DEVICE` - Inference device (auto, cuda, cpu)
- `NLM_FALLBACK_TO_API` - Enable API fallback

### 2. Models (`models/`)

#### NLMBaseModel

Wrapper for the fine-tuned language model:

```python
from mycosoft_mas.nlm.models import NLMBaseModel

model = NLMBaseModel()
await model.load()
response = await model.generate("What is Psilocybe cubensis?")
```

#### NLMEmbeddingModel

Embedding model for semantic search:

```python
from mycosoft_mas.nlm.models import NLMEmbeddingModel

embed_model = NLMEmbeddingModel()
embeddings = await embed_model.embed(["Agaricus bisporus", "Button mushroom"])
similarity = await embed_model.similarity("oyster mushroom", "Pleurotus ostreatus")
```

### 3. Training (`training/`)

The training pipeline supports:
- Data preparation from MINDEX and other sources
- LoRA fine-tuning for efficient adaptation
- Checkpoint management
- Model export for deployment

```python
from mycosoft_mas.nlm.training import NLMTrainer

trainer = NLMTrainer()

# Prepare training data
stats = await trainer.prepare_data()

# Train the model
results = await trainer.train(categories=["species_taxonomy", "mycology_research"])

# Export for deployment
trainer.export_model("/models/nlm/production", format="safetensors")
```

### 4. Inference (`inference/`)

The inference service provides:
- Model lifecycle management
- Text generation with domain specialization
- RAG-augmented queries via MINDEX
- Query type routing for optimized responses

```python
from mycosoft_mas.nlm import get_nlm_service
from mycosoft_mas.nlm.inference import PredictionRequest, QueryType

service = get_nlm_service()
await service.load_model()

request = PredictionRequest(
    text="What are the cultivation requirements for shiitake mushrooms?",
    query_type=QueryType.CULTIVATION,
    max_tokens=1024,
    temperature=0.7,
)

result = await service.predict(request)
print(result.text)
```

### 5. Data Loading (`datasets/`)

Utilities for loading and processing training data:

```python
from mycosoft_mas.nlm.datasets import NLMDataLoader, MINDEXConnector

# Load from local files
loader = NLMDataLoader()
examples = loader.load_all(categories=["species_taxonomy"])

# Fetch from MINDEX
connector = MINDEXConnector()
async for record in connector.fetch_for_training():
    print(record)
```

## API Endpoints

The NLM API is available at `/api/nlm/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/nlm/health` | GET | Health check and service status |
| `/api/nlm/predict` | POST | Generate prediction from query |
| `/api/nlm/model/info` | GET | Model capabilities and configuration |
| `/api/nlm/model/status` | GET | Service statistics and uptime |
| `/api/nlm/load` | POST | Load model into memory |
| `/api/nlm/unload` | POST | Unload model from memory |
| `/api/nlm/categories` | GET | List knowledge categories |
| `/api/nlm/training/status` | GET | Training status (if active) |

### Example API Usage

```bash
# Health check
curl http://192.168.0.188:8001/api/nlm/health

# Make a prediction
curl -X POST http://192.168.0.188:8001/api/nlm/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Describe the taxonomy of Agaricus bisporus",
    "query_type": "taxonomy",
    "max_tokens": 512
  }'

# Get model info
curl http://192.168.0.188:8001/api/nlm/model/info
```

## Knowledge Domains

The NLM is trained on the following categories:

1. **species_taxonomy** - Species names, classification, taxonomy
2. **mycology_research** - Research papers, findings, experiments
3. **environmental_sensors** - Environmental data with interpretations
4. **genetic_sequences** - DNA/RNA sequences and phenotypes
5. **ecological_interactions** - Species relationships, symbiosis
6. **geographic_distribution** - Where species are found
7. **cultivation_protocols** - How to grow fungi
8. **compound_chemistry** - Chemical compounds in fungi
9. **medical_applications** - Medicinal uses
10. **conservation_status** - Endangered species, conservation

## Query Types

Specialized query types for optimized responses:

| Type | Use Case |
|------|----------|
| `general` | General natural language queries |
| `species_id` | Species identification |
| `taxonomy` | Taxonomic classification |
| `ecology` | Ecological interactions |
| `cultivation` | Cultivation protocols |
| `research` | Research synthesis |
| `genetics` | Genetic analysis |

## Next Steps for Implementation

### Phase 1: Data Collection
- [ ] Connect data pipeline to MINDEX API
- [ ] Implement species data fetcher
- [ ] Implement research paper ingestion
- [ ] Add environmental sensor data formatting

### Phase 2: Model Training
- [ ] Set up training infrastructure (GPU, storage)
- [ ] Fine-tune base model (LLaMA 3.2 3B)
- [ ] Evaluate on held-out test set
- [ ] Export model for deployment

### Phase 3: Production Deployment
- [ ] Deploy model to GPU-enabled server
- [ ] Enable RAG with Qdrant embeddings
- [ ] Integrate with MAS orchestrator
- [ ] Add monitoring and logging

### Phase 4: Continuous Learning
- [ ] Implement feedback collection
- [ ] Set up continuous training pipeline
- [ ] Add active learning for edge cases
- [ ] Version model iterations

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NLM_MODEL_NAME` | `nlm` | Model identifier |
| `NLM_MODEL_VERSION` | `0.1.0` | Model version |
| `NLM_MODEL_DIR` | `/models/nlm` | Model weights directory |
| `NLM_CHECKPOINT_DIR` | `/models/nlm/checkpoints` | Checkpoint directory |
| `NLM_BASE_MODEL` | `meta-llama/Llama-3.2-3B` | Base model to fine-tune |
| `NLM_LEARNING_RATE` | `2e-5` | Training learning rate |
| `NLM_BATCH_SIZE` | `4` | Training batch size |
| `NLM_EPOCHS` | `3` | Training epochs |
| `NLM_MAX_LENGTH` | `2048` | Maximum sequence length |
| `NLM_DEVICE` | `auto` | Inference device |
| `NLM_ENABLE_RAG` | `true` | Enable RAG |
| `NLM_ENABLE_MEMORY` | `true` | Enable memory tracking |
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API URL |

## Related Documentation

- `docs/SYSTEM_REGISTRY_FEB04_2026.md` - System registry
- `docs/API_CATALOG_FEB04_2026.md` - API catalog
- `docs/MEMORY_DOCUMENTATION_INDEX_FEB05_2026.md` - Memory system

## Files Created

1. `mycosoft_mas/nlm/config.py` - Configuration classes
2. `mycosoft_mas/nlm/models/__init__.py` - Model exports
3. `mycosoft_mas/nlm/models/base_model.py` - NLMBaseModel, NLMEmbeddingModel
4. `mycosoft_mas/nlm/training/__init__.py` - Training exports
5. `mycosoft_mas/nlm/training/trainer.py` - NLMTrainer, DataCollator, TrainingMetrics
6. `mycosoft_mas/nlm/inference/__init__.py` - Inference exports
7. `mycosoft_mas/nlm/inference/service.py` - NLMService, PredictionRequest, PredictionResult
8. `mycosoft_mas/nlm/datasets/__init__.py` - Dataset exports
9. `mycosoft_mas/nlm/datasets/loaders.py` - NLMDataLoader, DataProcessor, MINDEXConnector
10. `mycosoft_mas/core/routers/nlm_api.py` - FastAPI router
11. `mycosoft_mas/nlm/__init__.py` - Updated module exports
12. `docs/NLM_FOUNDATION_FEB10_2026.md` - This documentation
