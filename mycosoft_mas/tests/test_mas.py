import pytest
from mycosoft_mas.core.agent_manager import AgentManager
from mycosoft_mas.core.base_agent import BaseAgent
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.core.task_manager import TaskManager

def test_agent_initialization():
    agent_manager = AgentManager()
    assert agent_manager is not None
    assert isinstance(agent_manager, AgentManager)

def test_knowledge_graph():
    kg = KnowledgeGraph()
    assert kg is not None
    assert isinstance(kg, KnowledgeGraph)

def test_task_manager():
    task_manager = TaskManager()
    assert task_manager is not None
    assert isinstance(task_manager, TaskManager)

def test_base_agent():
    agent = BaseAgent("test_agent")
    assert agent is not None
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == "test_agent" 