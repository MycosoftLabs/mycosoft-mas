"""
Mycosoft Multi-Agent System (MAS) - Configuration Settings
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"

# Create necessary directories
for directory in [DATA_DIR, LOGS_DIR, MODELS_DIR]:
    directory.mkdir(exist_ok=True)

# Database Settings
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "sqlite:///data/mycosoft.db"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
}

# Redis Settings
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
}

# API Settings
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("API_DEBUG", "False").lower() == "true",
    "reload": os.getenv("API_RELOAD", "False").lower() == "true",
}

# Blockchain Settings
BLOCKCHAIN_CONFIG = {
    "ethereum_rpc": os.getenv("ETH_RPC_URL"),
    "solana_rpc": os.getenv("SOLANA_RPC_URL"),
    "contract_addresses": {
        "dao": os.getenv("DAO_CONTRACT_ADDRESS"),
        "token": os.getenv("TOKEN_CONTRACT_ADDRESS"),
        "ip": os.getenv("IP_CONTRACT_ADDRESS"),
    },
}

# Agent Settings
AGENT_CONFIG = {
    "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
    "retry_interval": int(os.getenv("RETRY_INTERVAL", "300")),
    "max_retries": int(os.getenv("MAX_RETRIES", "3")),
}

# Logging Settings
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOGS_DIR / "mycosoft.log",
}

# Security Settings
SECURITY_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
    "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
}

# Machine Learning Settings
ML_CONFIG = {
    "model_path": MODELS_DIR,
    "device": os.getenv("ML_DEVICE", "cpu"),
    "batch_size": int(os.getenv("ML_BATCH_SIZE", "32")),
}

# Monitoring Settings
MONITORING_CONFIG = {
    "prometheus_port": int(os.getenv("PROMETHEUS_PORT", "9090")),
    "enable_tracing": os.getenv("ENABLE_TRACING", "False").lower() == "true",
}

def get_settings() -> Dict[str, Any]:
    """Get all settings as a dictionary."""
    return {
        "database": DATABASE_CONFIG,
        "redis": REDIS_CONFIG,
        "api": API_CONFIG,
        "blockchain": BLOCKCHAIN_CONFIG,
        "agent": AGENT_CONFIG,
        "logging": LOGGING_CONFIG,
        "security": SECURITY_CONFIG,
        "ml": ML_CONFIG,
        "monitoring": MONITORING_CONFIG,
    } 