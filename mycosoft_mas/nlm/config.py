"""
NLM Configuration Module - February 10, 2026

Configuration for the Nature Learning Model (NLM) - a domain-specific
language model for mycology and natural sciences.

Handles:
- Model configuration (paths, versions, architecture)
- Training hyperparameters
- Data paths and sources
- Environment variable overrides
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelArchitectureConfig:
    """Configuration for the NLM model architecture."""
    
    # Base model to fine-tune from
    base_model: str = "meta-llama/Llama-3.2-3B"
    
    # Model dimensions
    hidden_size: int = 3072
    num_hidden_layers: int = 28
    num_attention_heads: int = 24
    intermediate_size: int = 8192
    max_position_embeddings: int = 8192
    
    # Vocabulary
    vocab_size: int = 128256
    
    # LoRA configuration for efficient fine-tuning
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])


@dataclass
class TrainingConfig:
    """Configuration for NLM training."""
    
    # Hyperparameters
    learning_rate: float = 2e-5
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    effective_batch_size: int = 16  # batch_size * gradient_accumulation_steps
    epochs: int = 3
    max_steps: int = -1  # -1 means use epochs
    
    # Sequence settings
    max_length: int = 2048
    
    # Optimizer settings
    warmup_ratio: float = 0.03
    warmup_steps: int = 100
    weight_decay: float = 0.01
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    adam_epsilon: float = 1e-8
    max_grad_norm: float = 1.0
    
    # Learning rate scheduler
    lr_scheduler_type: str = "cosine"
    
    # Mixed precision
    fp16: bool = False
    bf16: bool = True  # Prefer bf16 on modern GPUs
    
    # Checkpointing
    save_strategy: str = "steps"
    save_steps: int = 500
    save_total_limit: int = 3
    
    # Evaluation
    eval_strategy: str = "steps"
    eval_steps: int = 500
    
    # Logging
    logging_steps: int = 10
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])


@dataclass
class DataConfig:
    """Configuration for NLM training data."""
    
    # Data paths
    training_data_dir: str = "/data/nlm/training"
    validation_data_dir: str = "/data/nlm/validation"
    test_data_dir: str = "/data/nlm/test"
    
    # Data sources for ingestion
    mindex_url: str = "http://192.168.0.189:8000"
    knowledge_graph_url: str = "http://192.168.0.189:6333"  # Qdrant
    
    # Data categories for mycology/nature domain
    categories: List[str] = field(default_factory=lambda: [
        "species_taxonomy",       # Species names, classification, taxonomy
        "mycology_research",      # Research papers, findings, experiments
        "environmental_sensors",  # Sensor data with natural language descriptions
        "genetic_sequences",      # DNA/RNA sequences and phenotype data
        "ecological_interactions", # Species relationships, symbiosis
        "geographic_distribution", # Where species are found
        "cultivation_protocols",   # How to grow fungi
        "compound_chemistry",      # Chemical compounds in fungi
        "medical_applications",    # Medicinal uses
        "conservation_status",     # Endangered species, conservation efforts
    ])
    
    # Quality filtering
    min_quality_score: float = 0.7
    min_text_length: int = 50
    max_text_length: int = 4096
    
    # Train/validation split
    validation_split: float = 0.1
    test_split: float = 0.05


@dataclass
class InferenceConfig:
    """Configuration for NLM inference."""
    
    # Model loading
    device: str = "auto"  # auto, cuda, cpu
    device_map: str = "auto"
    torch_dtype: str = "bfloat16"
    
    # Quantization for efficient inference
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    
    # Generation defaults
    default_max_tokens: int = 1024
    default_temperature: float = 0.7
    default_top_p: float = 0.9
    default_top_k: int = 50
    default_repetition_penalty: float = 1.1
    
    # Fallback to external API if local model unavailable
    fallback_to_api: bool = True
    fallback_model: str = "gpt-4o-mini"
    
    # Batch inference
    max_batch_size: int = 8


@dataclass
class NLMConfig:
    """
    Main configuration container for the Nature Learning Model.
    
    The NLM is a domain-specific language model specialized for:
    - Mycology and fungal biology
    - Species taxonomy and classification
    - Environmental and earth sciences
    - Genetic analysis and phenotypes
    - Ecological interactions and symbiosis
    - Conservation and sustainability
    """
    
    # Model identification
    model_name: str = "nlm"
    model_version: str = "0.1.0"
    model_display_name: str = "Nature Learning Model"
    model_description: str = "Domain-specific LLM for mycology and natural sciences"
    
    # Paths
    model_dir: str = "/models/nlm"
    checkpoint_dir: str = "/models/nlm/checkpoints"
    export_dir: str = "/models/nlm/exports"
    logs_dir: str = "/logs/nlm"
    
    # Sub-configurations
    architecture: ModelArchitectureConfig = field(default_factory=ModelArchitectureConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    
    # System prompt for NLM
    system_prompt: str = """You are NLM (Nature Learning Model), an AI specialized in:
- Mycology and fungal biology
- Species taxonomy and classification
- Environmental and earth sciences
- Genetic analysis and phenotypes
- Ecological interactions and symbiosis
- Conservation and sustainability

You are part of the Mycosoft Multi-Agent System (MAS), providing expert knowledge
about the natural world with a focus on fungi and their applications.

Provide accurate, scientifically-grounded responses based on the Mycosoft knowledge base."""
    
    # Feature flags
    enable_rag: bool = True  # Retrieval-augmented generation
    enable_memory: bool = True  # Use memory store for tracking
    enable_continuous_learning: bool = False  # Continuously learn from new data
    
    @classmethod
    def from_env(cls) -> "NLMConfig":
        """Load configuration with environment variable overrides."""
        config = cls()
        
        # Model identification
        config.model_name = os.getenv("NLM_MODEL_NAME", config.model_name)
        config.model_version = os.getenv("NLM_MODEL_VERSION", config.model_version)
        
        # Paths
        config.model_dir = os.getenv("NLM_MODEL_DIR", config.model_dir)
        config.checkpoint_dir = os.getenv("NLM_CHECKPOINT_DIR", config.checkpoint_dir)
        config.export_dir = os.getenv("NLM_EXPORT_DIR", config.export_dir)
        config.logs_dir = os.getenv("NLM_LOGS_DIR", config.logs_dir)
        
        # Architecture overrides
        config.architecture.base_model = os.getenv(
            "NLM_BASE_MODEL", config.architecture.base_model
        )
        config.architecture.use_lora = os.getenv(
            "NLM_USE_LORA", "true"
        ).lower() == "true"
        
        # Training overrides
        if lr := os.getenv("NLM_LEARNING_RATE"):
            config.training.learning_rate = float(lr)
        if bs := os.getenv("NLM_BATCH_SIZE"):
            config.training.batch_size = int(bs)
        if epochs := os.getenv("NLM_EPOCHS"):
            config.training.epochs = int(epochs)
        if max_len := os.getenv("NLM_MAX_LENGTH"):
            config.training.max_length = int(max_len)
        
        # Data paths
        config.data.training_data_dir = os.getenv(
            "NLM_TRAINING_DATA_DIR", config.data.training_data_dir
        )
        config.data.mindex_url = os.getenv(
            "MINDEX_API_URL", config.data.mindex_url
        )
        
        # Inference settings
        config.inference.device = os.getenv("NLM_DEVICE", config.inference.device)
        config.inference.fallback_to_api = os.getenv(
            "NLM_FALLBACK_TO_API", "true"
        ).lower() == "true"
        
        # Feature flags
        config.enable_rag = os.getenv("NLM_ENABLE_RAG", "true").lower() == "true"
        config.enable_memory = os.getenv("NLM_ENABLE_MEMORY", "true").lower() == "true"
        
        return config
    
    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for path_attr in ["model_dir", "checkpoint_dir", "export_dir", "logs_dir"]:
            path = Path(getattr(self, path_attr))
            path.mkdir(parents=True, exist_ok=True)
        
        # Also create data directories
        Path(self.data.training_data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.data.validation_data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.data.test_data_dir).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check model version format
        if not self.model_version or len(self.model_version.split(".")) < 2:
            errors.append("model_version must be in semver format (e.g., 0.1.0)")
        
        # Check training hyperparameters
        if self.training.learning_rate <= 0:
            errors.append("learning_rate must be positive")
        if self.training.batch_size < 1:
            errors.append("batch_size must be at least 1")
        if self.training.epochs < 1 and self.training.max_steps < 1:
            errors.append("Either epochs or max_steps must be positive")
        
        # Check data paths exist (optional - may be created later)
        # if not Path(self.data.training_data_dir).exists():
        #     errors.append(f"Training data directory not found: {self.data.training_data_dir}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_display_name": self.model_display_name,
            "model_description": self.model_description,
            "model_dir": self.model_dir,
            "checkpoint_dir": self.checkpoint_dir,
            "export_dir": self.export_dir,
            "logs_dir": self.logs_dir,
            "architecture": {
                "base_model": self.architecture.base_model,
                "hidden_size": self.architecture.hidden_size,
                "num_hidden_layers": self.architecture.num_hidden_layers,
                "use_lora": self.architecture.use_lora,
                "lora_r": self.architecture.lora_r,
            },
            "training": {
                "learning_rate": self.training.learning_rate,
                "batch_size": self.training.batch_size,
                "epochs": self.training.epochs,
                "max_length": self.training.max_length,
            },
            "data": {
                "training_data_dir": self.data.training_data_dir,
                "categories": self.data.categories,
            },
            "inference": {
                "device": self.inference.device,
                "fallback_to_api": self.inference.fallback_to_api,
            },
            "enable_rag": self.enable_rag,
            "enable_memory": self.enable_memory,
        }


# Global config instance
_config: Optional[NLMConfig] = None


def get_nlm_config() -> NLMConfig:
    """Get the global NLM configuration instance."""
    global _config
    if _config is None:
        _config = NLMConfig.from_env()
        logger.info(f"NLM Config loaded: {_config.model_name} v{_config.model_version}")
    return _config


def reset_nlm_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
