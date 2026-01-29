#!/usr/bin/env python3
"""Start PersonaPlex Moshi server with proper path setup for RTX 5090."""

import sys
import os

# CRITICAL: Disable torch.compile (Triton not compatible with RTX 5090 sm_120)
os.environ['NO_TORCH_COMPILE'] = '1'
os.environ['NO_CUDA_GRAPH'] = '1'  # Also disable CUDA graphs for stability
os.environ['TORCHDYNAMO_DISABLE'] = '1'  # Alternative disable flag

# Set CUDA device
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Add PersonaPlex moshi to path
personaplex_path = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\personaplex-repo\moshi"
sys.path.insert(0, personaplex_path)

# Change to the moshi directory so voice prompts can be found
os.chdir(personaplex_path)

print("=" * 60)
print("PersonaPlex Server Startup")
print("=" * 60)
print(f"NO_TORCH_COMPILE = {os.environ.get('NO_TORCH_COMPILE')}")
print(f"NO_CUDA_GRAPH = {os.environ.get('NO_CUDA_GRAPH')}")
print(f"TORCHDYNAMO_DISABLE = {os.environ.get('TORCHDYNAMO_DISABLE')}")
print(f"CUDA_VISIBLE_DEVICES = {os.environ.get('CUDA_VISIBLE_DEVICES')}")
print(f"Working directory: {personaplex_path}")
print(f"Python path[0]: {sys.path[0]}")
print("=" * 60)
print("Starting PersonaPlex on RTX 5090...")
print("=" * 60)

# Import and run the server
from moshi.server import main
main()
