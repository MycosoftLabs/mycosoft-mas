import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.agents.base_agent import BaseAgent

@pytest.fixture
def knowledge_graph():
    return KnowledgeGraph()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

def test_knowledge_graph_initialization(knowledge_graph):
    assert knowledge_graph.graph is not None
    assert knowledge_graph.last_update is not None
    assert knowledge_graph.agent_count == 0
    assert knowledge_graph.active_agents == 0

def test_add_agent(knowledge_graph, mock_agent):
    knowledge_graph.add_agent(mock_agent)
    assert mock_agent.agent_id in knowledge_graph.graph.nodes
    assert knowledge_graph.agent_count == 1
    assert knowledge_graph.active_agents == 1

def test_remove_agent(knowledge_graph, mock_agent):
    knowledge_graph.add_agent(mock_agent)
    knowledge_graph.remove_agent(mock_agent.agent_id)
    assert mock_agent.agent_id not in knowledge_graph.graph.nodes
    assert knowledge_graph.agent_count == 0
    assert knowledge_graph.active_agents == 0

def test_add_relationship(knowledge_graph, mock_agent):
    agent2 = Mock(spec=BaseAgent)
    agent2.agent_id = "test_agent2"
    agent2.capabilities = ["test_capability2"]
    
    knowledge_graph.add_agent(mock_agent)
    knowledge_graph.add_agent(agent2)
    knowledge_graph.add_relationship(mock_agent.agent_id, agent2.agent_id, "test_relationship")
    
    assert knowledge_graph.graph.has_edge(mock_agent.agent_id, agent2.agent_id)
    assert knowledge_graph.graph.edges[mock_agent.agent_id, agent2.agent_id]["type"] == "test_relationship"

def test_remove_relationship(knowledge_graph, mock_agent):
    agent2 = Mock(spec=BaseAgent)
    agent2.agent_id = "test_agent2"
    agent2.capabilities = ["test_capability2"]
    
    knowledge_graph.add_agent(mock_agent)
    knowledge_graph.add_agent(agent2)
    knowledge_graph.add_relationship(mock_agent.agent_id, agent2.agent_id, "test_relationship")
    knowledge_graph.remove_relationship(mock_agent.agent_id, agent2.agent_id)
    
    assert not knowledge_graph.graph.has_edge(mock_agent.agent_id, agent2.agent_id)

def test_get_agent_relationships(knowledge_graph, mock_agent):
    agent2 = Mock(spec=BaseAgent)
    agent2.agent_id = "test_agent2"
    agent2.capabilities = ["test_capability2"]
    
    knowledge_graph.add_agent(mock_agent)
    knowledge_graph.add_agent(agent2)
    knowledge_graph.add_relationship(mock_agent.agent_id, agent2.agent_id, "test_relationship")
    
    relationships = knowledge_graph.get_agent_relationships(mock_agent.agent_id)
    assert len(relationships) == 1
    assert relationships[0]["target"] == agent2.agent_id
    assert relationships[0]["type"] == "test_relationship"

def test_to_json(knowledge_graph, mock_agent):
    knowledge_graph.add_agent(mock_agent)
    json_data = knowledge_graph.to_json()
    
    assert "nodes" in json_data
    assert "edges" in json_data
    assert "metadata" in json_data
    assert len(json_data["nodes"]) == 1
    assert len(json_data["edges"]) == 0
    assert json_data["metadata"]["agent_count"] == 1
    assert json_data["metadata"]["active_agents"] == 1

def test_from_json(knowledge_graph, mock_agent):
    knowledge_graph.add_agent(mock_agent)
    json_data = knowledge_graph.to_json()
    
    new_graph = KnowledgeGraph()
    new_graph.from_json(json_data)
    
    assert mock_agent.agent_id in new_graph.graph.nodes
    assert new_graph.agent_count == 1
    assert new_graph.active_agents == 1 