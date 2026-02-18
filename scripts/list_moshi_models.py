#!/usr/bin/env python3
"""List available Moshi models on HuggingFace."""
from huggingface_hub import HfApi

api = HfApi()

# Search for kyutai models
print("Kyutai Moshi models on HuggingFace:")
for model in api.list_models(author="kyutai"):
    print(f"  - {model.id}")
