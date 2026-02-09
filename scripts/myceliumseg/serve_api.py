#!/usr/bin/env python3
"""
Standalone MyceliumSeg API server (Phase 0).
Run: MINDEX_DATABASE_URL=... python -m scripts.myceliumseg.serve_api
     or: uvicorn scripts.myceliumseg.serve_api:app --host 0.0.0.0 --port 8010
Serves /mindex/myceliumseg/images, /mindex/myceliumseg/validation/jobs, etc.
"""
from __future__ import annotations

import os
import sys

# Ensure project root on path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(_here))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    app = None  # type: ignore
else:
    from scripts.myceliumseg.api_routes import build_router
    app = FastAPI(title="MyceliumSeg API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(build_router(), prefix="/mindex")


def main():
    if app is None:
        print("Install FastAPI and uvicorn: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)
    import uvicorn
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
