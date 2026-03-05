"""
MYCA OS Entry Point — Run with: python -m mycosoft_mas.myca.os

This starts the MYCA Operating System daemon on VM 191.
MYCA will boot, connect to all systems, and begin autonomous operation.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Log directory: /opt/myca/logs on VM 191, else local
LOG_DIR = Path(os.getenv("MYCA_LOG_DIR", "/opt/myca/logs"))
if not LOG_DIR.exists():
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        LOG_DIR = Path.cwd() / "logs"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "myca_os.log"

def _gateway_log_handler():
    """Handler that feeds logs to the gateway buffer for /logs and WebSocket."""
    from mycosoft_mas.myca.os.gateway import log_to_buffer

    class GatewayHandler(logging.Handler):
        def emit(self, record):
            try:
                log_to_buffer(self.format(record))
            except Exception:
                pass

    h = GatewayHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
    return h

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), mode="a"),
    ],
)
# Add gateway handler so /logs and WebSocket get real-time logs
try:
    logging.getLogger().addHandler(_gateway_log_handler())
except Exception:
    pass

# Suppress noisy loggers
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


def main():
    from mycosoft_mas.myca.os.core import MycaOS

    print("=" * 60)
    print("  MYCA Operating System")
    print("  VM 191 — 192.168.0.191")
    print("  Roles: COO, Co-CEO, Co-CTO")
    print("=" * 60)
    print()

    os_instance = MycaOS()
    asyncio.run(os_instance.run())


if __name__ == "__main__":
    main()
