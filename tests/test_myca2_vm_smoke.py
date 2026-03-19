"""
MYCA2 / PSILO smoke against live MAS + MINDEX on LAN.

Run only when you can reach VMs and want end-to-end checks:

  MYCA2_VM_SMOKE=1 poetry run pytest tests/test_myca2_vm_smoke.py -v

Optional: MAS_API_URL, MINDEX_API_URL (defaults 188:8001, 189:8000).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_rollout_smoke():
    path = REPO_ROOT / "scripts" / "myca2_vm_rollout.py"
    spec = importlib.util.spec_from_file_location("myca2_vm_rollout", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.smoke_test


@pytest.mark.skipif(
    os.environ.get("MYCA2_VM_SMOKE") != "1",
    reason="Set MYCA2_VM_SMOKE=1 to run LAN MYCA2 smoke (MAS 188 + MINDEX 189)",
)
def test_myca2_psilo_session_smoke():
    smoke_test = _load_rollout_smoke()
    ok = smoke_test()
    assert ok is True, "smoke_test failed: MAS health, MINDEX db, PSILO start+get"
