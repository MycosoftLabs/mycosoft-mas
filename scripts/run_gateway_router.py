#!/usr/bin/env python3
"""
Run the 4GB Jetson gateway router service.

Example:
  python scripts/run_gateway_router.py --host 0.0.0.0 --port 8120
"""

from __future__ import annotations

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MycoBrain gateway router service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8120)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("mycosoft_mas.edge.gateway_router:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
