#!/usr/bin/env python3
"""Start only the GPU gateway server."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.local_gpu_services import create_gateway, PORTS

if __name__ == "__main__":
    print("Starting GPU Gateway on port 8300...")
    app, uvicorn = create_gateway()
    uvicorn.run(app, host="0.0.0.0", port=PORTS["gateway"], log_level="info")
