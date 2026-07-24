"""One-shot entry point for the independently scheduled boundary scan."""

from __future__ import annotations

import asyncio
import logging

from mycosoft_mas.soc.gws_boundary_scan import BoundaryScanService


async def main() -> None:
    result = await BoundaryScanService().run_once()
    logging.getLogger(__name__).info(
        "Google Workspace boundary scan completed: status=%s hit_count=%s",
        result["status"],
        result["hit_count"],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
