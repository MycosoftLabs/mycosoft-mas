"""Agent100 caps and defaults — MAY03_2026."""

import os
from pathlib import Path

AGENT100_DEFAULT_WORLDBASE = os.environ.get("AGENT100_WORLDBASE_URL", "https://mycosoft.com").rstrip("/")

_REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT100_DATA_DIR = Path(os.environ.get("AGENT100_DATA_DIR", str(_REPO_ROOT / "data" / "agent100")))
AGENT100_CONFIG_PATH = Path(
    os.environ.get(
        "AGENT100_CONFIG_PATH",
        str(_REPO_ROOT / "mycosoft_mas" / "agent100" / "configs" / "agents_matrix.yaml"),
    )
)


def global_cap_cents() -> int:
    return int(os.environ.get("AGENT100_GLOBAL_CAP_CENTS", "500000"))


def per_agent_cap_cents() -> int:
    return int(os.environ.get("AGENT100_PER_AGENT_CAP_CENTS", "20000"))


def fleet_rpm() -> int:
    return int(os.environ.get("AGENT100_FLEET_RPM", "2000"))


def agent_rpm() -> int:
    return int(os.environ.get("AGENT100_AGENT_RPM", "30"))
