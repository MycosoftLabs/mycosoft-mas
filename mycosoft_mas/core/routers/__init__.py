from .agents import router as agents
from .tasks import router as tasks
from .dashboard import router as dashboard
from .integrations import router as integrations
from .search_memory_api import router as search_memory
from .earth2_memory_api import router as earth2_memory
from .voice_command_api import router as voice_command
from .timeline_api import router as timeline
from .prediction_api import router as prediction
from .knowledge_graph_api import router as knowledge_graph
from .physicsnemo_api import router as physicsnemo
from .fci_api import router as fci
from .fci_websocket import router as fci_websocket

__all__ = [
    "agents",
    "tasks",
    "dashboard",
    "integrations",
    "search_memory",
    "earth2_memory",
    "voice_command",
    "timeline",
    "prediction",
    "knowledge_graph",
    "physicsnemo",
    "fci",
    "fci_websocket",
]
