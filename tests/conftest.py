import pytest
import asyncio
import sys
import types
import os
from unittest.mock import Mock, patch

# Stub out heavy optional dependencies to keep tests lightweight
os.environ.setdefault("MAS_LIGHT_IMPORT", "1")

# Note: 'requests' removed from stub list to allow test_n8n_earth2_workflows.py to work
for _mod in [
    "spacy",
    "pyautogui",
    "selenium",
    "undetected_chromedriver",
    "web3",
    "bitcoin",
    "eth_account",
    # "requests",  # Needed for n8n workflow tests
    "docx",
    "PyPDF2",
    "bs4",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

if "web3" in sys.modules:
    class _Web3:
        pass
    sys.modules["web3"].Web3 = _Web3

if "eth_account" in sys.modules:
    class _Account:
        pass
    sys.modules["eth_account"].Account = _Account

if "bitcoin" in sys.modules:
    sys.modules["bitcoin"].__all__ = []

if "docx" in sys.modules:
    docx_mod = sys.modules["docx"]
    shared_mod = types.ModuleType("docx.shared")
    class _Pt:
        def __init__(self, *args, **kwargs):
            pass
    class _Inches:
        def __init__(self, *args, **kwargs):
            pass
    shared_mod.Pt = _Pt
    shared_mod.Inches = _Inches
    sys.modules["docx.shared"] = shared_mod


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    redis.get = Mock(return_value=None)
    redis.set = Mock(return_value=True)
    redis.delete = Mock(return_value=True)
    return redis