import pytest

from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.services.event_ingestion_service import EventIngestionService


@pytest.mark.asyncio
async def test_process_event_adds_node_and_edge():
    kg = KnowledgeGraph()
    await kg.initialize()
    service = EventIngestionService(kg)

    event = {
        "id": "event1",
        "type": "env.v1",
        "source": "device123",
        "data": {"temperature": 21.5},
    }

    await service.process_event(event)

    assert "event1" in kg.graph
    assert kg.graph.has_edge("device123", "event1")
    metadata = kg.get_agent_metadata("event1")
    assert metadata["event_type"] == "env.v1"
    assert metadata["data"]["temperature"] == 21.5
