import pytest
import asyncio
import sys
import types
import os
from unittest.mock import Mock, patch

# Stub out heavy optional dependencies to keep tests lightweight
os.environ.setdefault("MAS_LIGHT_IMPORT", "1")

for _mod in [
    "spacy",
    "pyautogui",
    "selenium",
    "undetected_chromedriver",
    "web3",
    "bitcoin",
    "eth_account",
    "requests",
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
    docx_mod.shared = shared_mod
    sys.modules["docx.shared"] = shared_mod
    enum_mod = types.ModuleType("docx.enum")
    text_mod = types.ModuleType("docx.enum.text")
    text_mod.WD_ALIGN_PARAGRAPH = object()
    enum_mod.text = text_mod
    sys.modules["docx.enum"] = enum_mod
    sys.modules["docx.enum.text"] = text_mod
    
if "bs4" in sys.modules:
    bs4_mod = sys.modules["bs4"]
    class _BeautifulSoup:
        def __init__(self, *args, **kwargs):
            pass
    bs4_mod.BeautifulSoup = _BeautifulSoup

if "selenium" in sys.modules:
    sel_mod = sys.modules["selenium"]
    webdriver_mod = types.ModuleType("selenium.webdriver")
    chrome_mod = types.ModuleType("selenium.webdriver.chrome")
    options_mod = types.ModuleType("selenium.webdriver.chrome.options")
    common_mod = types.ModuleType("selenium.webdriver.common")
    by_mod = types.ModuleType("selenium.webdriver.common.by")
    support_mod = types.ModuleType("selenium.webdriver.support")
    ui_mod = types.ModuleType("selenium.webdriver.support.ui")
    class _WebDriverWait:
        def __init__(self, *args, **kwargs):
            pass
    ui_mod.WebDriverWait = _WebDriverWait
    support_mod.ui = ui_mod
    ec_mod = types.ModuleType("selenium.webdriver.support.expected_conditions")
    support_mod.expected_conditions = ec_mod
    class _By:
        ID = "id"
    by_mod.By = _By
    common_mod.by = by_mod
    class _Options:
        def __init__(self, *args, **kwargs):
            pass
    options_mod.Options = _Options
    chrome_mod.options = options_mod
    webdriver_mod.chrome = chrome_mod
    webdriver_mod.common = common_mod
    webdriver_mod.support = support_mod
    sel_mod.webdriver = webdriver_mod
    sys.modules["selenium.webdriver"] = webdriver_mod
    sys.modules["selenium.webdriver.chrome"] = chrome_mod
    sys.modules["selenium.webdriver.chrome.options"] = options_mod
    sys.modules["selenium.webdriver.common"] = common_mod
    sys.modules["selenium.webdriver.common.by"] = by_mod
    sys.modules["selenium.webdriver.support"] = support_mod
    sys.modules["selenium.webdriver.support.ui"] = ui_mod
    sys.modules["selenium.webdriver.support.expected_conditions"] = ec_mod

# Provide minimal stubs for sentence_transformers package
if "sentence_transformers" not in sys.modules:
    st_mod = types.ModuleType("sentence_transformers")
    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass
    st_mod.SentenceTransformer = _Dummy
    util_mod = types.ModuleType("sentence_transformers.util")
    st_mod.util = util_mod
    sys.modules["sentence_transformers"] = st_mod
    sys.modules["sentence_transformers.util"] = util_mod

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.core.agent_manager import AgentManager
from mycosoft_mas.core.task_manager import TaskManager
from mycosoft_mas.core.metrics_collector import MetricsCollector

# Import Orchestrator lazily to avoid heavy dependencies when not needed
Orchestrator = None
from mycosoft_mas.core.cluster import Cluster
from mycosoft_mas.services.integration_service import IntegrationService

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    agent.status = "running"
    agent.get_status.return_value = {
        "status": "running",
        "capabilities": ["test_capability"],
        "task_count": 0
    }
    return agent

@pytest.fixture
def orchestrator():
    """Create a new orchestrator instance for testing."""
    global Orchestrator
    if Orchestrator is None:
        from mycosoft_mas.orchestrator import Orchestrator as Orc
        Orchestrator = Orc
    return Orchestrator()

@pytest.fixture
def cluster():
    """Create a new cluster instance for testing."""
    return Cluster("test_cluster", "Test Cluster")

@pytest.fixture
def integration_service():
    """Create an integration service instance for testing."""
    config = {
        "data_dir": "test_data",
        "websocket_host": "localhost",
        "websocket_port": 8765,
        "metrics_interval": 1.0
    }
    return IntegrationService(config)

@pytest.fixture
def mock_agent_manager():
    manager = Mock(spec=AgentManager)
    manager.get_status.return_value = {
        "status": "running",
        "agent_count": 1,
        "task_queue_size": 0
    }
    return manager

@pytest.fixture
def mock_task_manager():
    manager = Mock(spec=TaskManager)
    manager.get_status.return_value = {
        "status": "running",
        "tasks_pending": 0,
        "tasks_completed": 0
    }
    return manager

@pytest.fixture
def mock_metrics_collector():
    collector = Mock(spec=MetricsCollector)
    collector.get_status.return_value = {
        "status": "running",
        "metrics": {},
        "alerts": []
    }
    return collector

@pytest.fixture
def mock_task():
    return {
        "type": "test_task",
        "data": "test_data",
        "priority": "high",
        "timestamp": "2024-04-19T00:00:00Z"
    }

@pytest.fixture
def mock_config():
    return {
        "agent_manager": {
            "url": "http://localhost:8000",
            "monitoring_interval": 60
        },
        "task_manager": {
            "monitoring_interval": 60
        },
        "monitoring": {
            "enabled": True,
            "alert_threshold": 80
        },
        "security": {
            "enabled": True,
            "auth_timeout": 3600
        },
        "dependencies": {
            "auto_update": True,
            "update_interval": 3600
        },
        "data_dir": "test_data",
        "websocket_host": "localhost",
        "websocket_port": 8765,
        "metrics_interval": 1.0
    }

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """Set up the test environment."""
    # Create test data directory
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Set up environment variables
    with patch.dict('os.environ', {
        'MAS_DATA_DIR': str(test_data_dir),
        'MAS_ENV': 'test',
        'MAS_LIGHT_IMPORT': '1'
    }):
        yield
