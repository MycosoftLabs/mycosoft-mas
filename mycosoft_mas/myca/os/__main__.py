"""
MYCA OS Entry Point — Run with: python -m mycosoft_mas.myca.os

This starts the MYCA Operating System daemon on VM 191.
MYCA will boot, connect to all systems, and begin autonomous operation.
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/opt/myca/logs/myca_os.log", mode="a"),
    ],
)

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
