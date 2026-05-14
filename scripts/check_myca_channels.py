"""Non-secret MYCA channel/environment verifier."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import credentials_loader

    credentials_loader.load_credentials_local()
except Exception:
    pass


def _load_channel_status():
    path = ROOT / "mycosoft_mas" / "myca" / "os" / "channels_health.py"
    spec = importlib.util.spec_from_file_location("myca_channels_health_check", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.get_all_channel_status


async def _main() -> int:
    get_all_channel_status = _load_channel_status()
    report = await get_all_channel_status()
    print(json.dumps(report, indent=2, sort_keys=True))
    channels = report.get("channels", {})
    return 0 if any(data.get("connected") for data in channels.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
