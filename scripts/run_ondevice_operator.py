#!/usr/bin/env python3
"""
Run the on-device Jetson operator runtime (between Side A and Side B).

Example:
  python scripts/run_ondevice_operator.py --host 0.0.0.0 --port 8110
"""

from __future__ import annotations

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MycoBrain on-device operator service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8110)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("mycosoft_mas.edge.ondevice_operator:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
