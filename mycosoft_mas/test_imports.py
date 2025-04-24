try:
    from mycosoft_mas.core.agent_manager import AgentManager
    print("AgentManager import successful")
except Exception as e:
    print(f"Error importing AgentManager: {str(e)}")

try:
    from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
    print("KnowledgeGraph import successful")
except Exception as e:
    print(f"Error importing KnowledgeGraph: {str(e)}")

try:
    from mycosoft_mas.core.metrics_collector import MetricsCollector
    print("MetricsCollector import successful")
except Exception as e:
    print(f"Error importing MetricsCollector: {str(e)}")

try:
    from mycosoft_mas.core.task_manager import TaskManager
    print("TaskManager import successful")
except Exception as e:
    print(f"Error importing TaskManager: {str(e)}") 