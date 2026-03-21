from .agents import router as agents
from .dashboard import router as dashboard
from .earth2_memory_api import router as earth2_memory
from .fci_api import router as fci
from .fci_websocket import router as fci_websocket
from .governance_api import router as governance
from .integrations import router as integrations
from .knowledge_graph_api import router as knowledge_graph
from .physicsnemo_api import router as physicsnemo
from .prediction_api import router as prediction
from .provenance_api import router as provenance
from .search_memory_api import router as search_memory
from .tasks import router as tasks
from .timeline_api import router as timeline
from .voice_command_api import router as voice_command

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
    "provenance",
    "governance",
]
