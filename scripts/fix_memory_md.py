doc_path = r'c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\MEMORY.md'
with open(doc_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_learn = 'await self.learn_fact("Amanita muscaria contains ibotenic acid")'
new_learn = 'await self.learn_fact({"subject": "Amanita muscaria", "predicate": "contains", "object": "ibotenic acid"})'
text = text.replace(old_learn, new_learn)

if 'persistent_graph.py' not in text:
    text += "\n| `memory/persistent_graph.py` | Persistent knowledge graph |\n"
    text += "| `memory/analytics.py` | Memory analytics |\n"
    text += "| `memory/user_context.py` | User context memory |\n"
    text += "| `memory/autobiographical.py` | Autobiographical memory |\n"
    text += "| `memory/cleanup.py` | Memory cleanup tasks |\n"
    text += "| `memory/earth2_memory.py` | Earth2 specific memory |\n"
    text += "| `memory/export.py` | Memory export tools |\n"
    text += "| `memory/fungal_memory_bridge.py` | Fungal network memory bridge |\n"
    text += "| `memory/gpu_memory.py` | GPU memory integration |\n"
    text += "| `memory/graph_indexer.py` | Graph memory indexer |\n"
    text += "| `memory/graph_schema.py` | Graph memory schema |\n"
    text += "| `memory/langgraph_checkpointer.py` | LangGraph checkpointer |\n"
    text += "| `memory/long_term.py` | Long term memory |\n"
    text += "| `memory/mem0_adapter.py` | Mem0 adapter |\n"
    text += "| `memory/openviking_bridge.py` | OpenViking bridge |\n"
    text += "| `memory/openviking_sync.py` | OpenViking sync |\n"
    text += "| `memory/short_term.py` | Short term memory |\n"
    text += "| `memory/temporal_patterns.py` | Temporal memory patterns |\n"
    text += "| `memory/voice_search_memory.py` | Voice search memory |\n"
    
    text += "\n### Memory API Routers\n"
    text += "| `core/routers/memory_api.py` | Memory API routing |\n"
    text += "| `core/routers/memory_integration_api.py` | Integration API |\n"
    text += "| `core/routers/conversation_memory_api.py` | Conversation Memory API |\n"
    text += "| `core/routers/earth2_memory_api.py` | Earth2 Memory API |\n"
    text += "| `core/routers/search_memory_api.py` | Search Memory API |\n"
    text += "| `core/routers/memory_updates_ws.py` | Memory Updates WebSocket |\n"

with open(doc_path, 'w', encoding='utf-8') as f:
    f.write(text)
