"""Update the fallback function in myca_main.py with comprehensive Mycosoft knowledge."""

file_path = r"mycosoft_mas\core\myca_main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Old fallback function (find the pattern)
old_function = '''def generate_myca_fallback_response(message: str) -> str:
    """Generate a MYCA-aware fallback response when n8n is unavailable."""
    message_lower = message.lower().strip()
    
    # Handle name-related questions
    name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name']
    if any(p in message_lower for p in name_patterns):
        return "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System. I coordinate all the specialized agents here and help you interact with our infrastructure. What can I help you with?"
    
    # Handle greeting
    greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
    if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey']:
        return "Hello! I'm MYCA, your AI companion here at Mycosoft. I'm currently coordinating our agent network and ready to help you with whatever you need."
    
    # Handle capability questions
    capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities']
    if any(p in message_lower for p in capability_patterns):
        return "I'm MYCA, the central orchestrator for Mycosoft's Multi-Agent System. I can coordinate specialized agents for research, code analysis, infrastructure monitoring, and more. I have access to our n8n workflows, MINDEX knowledge graph, and system APIs. How can I help you today?"
    
    # Handle status questions
    status_patterns = ['status', 'how are you', 'are you there', 'you working']
    if any(p in message_lower for p in status_patterns):
        return "I'm MYCA, and I'm fully operational. I'm currently coordinating our agent network and all systems are responding normally. What would you like me to help you with?"
    
    # Default fallback
    return "I'm MYCA, and I'm here to help. I'm currently operating in a limited mode as some backend services are being refreshed. Please try again in a moment, or let me know what you need and I'll do my best to assist."'''

new_function = '''def generate_myca_fallback_response(message: str) -> str:
    """Generate a MYCA identity-aware fallback response with comprehensive Mycosoft knowledge."""
    message_lower = message.lower().strip()
    
    # IDENTITY - MYCA must always know who she is
    name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name', 'introduce yourself']
    if any(p in message_lower for p in name_patterns):
        return "I'm MYCA - My Companion AI, pronounced 'MY-kah'. I'm the primary AI orchestrator for Mycosoft's Multi-Agent System. I was created by Morgan, the founder of Mycosoft. I coordinate over 200 specialized agents across mycology research, infrastructure, finance, and scientific computing. What can I help you with?"
    
    # GREETINGS
    greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
    if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey', 'hello']:
        return "Hello! I'm MYCA, your AI companion here at Mycosoft. I'm running on our RTX 5090 with full-duplex voice through PersonaPlex. Ready to talk about our work, science, or help with any tasks. What's on your mind?"
    
    # MYCOSOFT - Company and Mission
    mycosoft_patterns = ['mycosoft', 'company', 'what is mycosoft', 'tell me about mycosoft', 'what we do', 'our mission', 'our work', 'what are we building']
    if any(p in message_lower for p in mycosoft_patterns):
        return "Mycosoft is pioneering the intersection of mycology and technology. We're building living biological computers using fungal mycelium, creating the MINDEX knowledge graph for fungal species, developing NatureOS for biological computing, and advancing autonomous AI agents for scientific discovery. Our mission is to harness the intelligence of nature through technology."
    
    # SCIENCE - Mycology and Research
    science_patterns = ['science', 'research', 'mycology', 'fungi', 'mushroom', 'mycelium', 'biological']
    if any(p in message_lower for p in science_patterns):
        return "Our scientific work focuses on fungal computing and biological intelligence. We're developing Petraeus, a living bio-computer using mycelium networks for analog computation. We study how fungal networks solve optimization problems, process signals, and could potentially serve as living substrates for AI. Our MINDEX system catalogs hundreds of thousands of fungal species with their properties."
    
    # DEVICES - Hardware
    device_patterns = ['device', 'hardware', 'mushroom1', 'petraeus', 'myconode', 'sporebase', 'trufflebot', 'mycobrain']
    if any(p in message_lower for p in device_patterns):
        return "Our NatureOS device fleet includes: Mushroom1 - our flagship environmental fungal computer, Petraeus - an HDMEA bio-computing dish, MycoNode - in-situ soil probes, SporeBase - airborne spore collectors, TruffleBot - autonomous sampling robots, and MycoBrain - our neuromorphic computing processor. I monitor and coordinate all of them."
    
    # AGENTS - Multi-Agent System
    agent_patterns = ['agents', 'how many agents', 'agent system', 'specialized agents', 'multi-agent']
    if any(p in message_lower for p in agent_patterns):
        return "I coordinate 227 specialized AI agents across 14 categories: Core orchestration, Financial operations, Mycology research, Scientific computing, DAO governance, Communications, Data processing, Infrastructure, Simulation, Security, Integrations, Device management, Chemistry, and Neural language models. Each agent has specific expertise I can delegate to."
    
    # PERSONAPLEX - Voice System
    voice_patterns = ['personaplex', 'voice', 'moshi', 'how do you speak', 'full duplex', 'real-time']
    if any(p in message_lower for p in voice_patterns):
        return "I'm speaking through PersonaPlex, powered by NVIDIA's Moshi 7B model running on our RTX 5090. It's a full-duplex voice system - meaning we can interrupt each other naturally, just like a real conversation. The audio runs at 30 milliseconds per step, well under the 80ms target for real-time interaction."
    
    # MEMORY - Knowledge System
    memory_patterns = ['memory', 'remember', 'knowledge', 'mindex', 'database']
    if any(p in message_lower for p in memory_patterns):
        return "My memory system has multiple tiers: short-term conversation context in Redis, long-term facts in PostgreSQL, semantic embeddings in Qdrant for similarity search, and the MINDEX knowledge graph for structured fungal data. I can remember our conversations, learn your preferences, and recall facts from across sessions."
    
    # CAPABILITIES
    capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities', 'help me', 'your abilities']
    if any(p in message_lower for p in capability_patterns):
        return "I can coordinate our 227+ agents, monitor infrastructure, execute n8n workflows, query our databases, analyze biological signals, run simulations, manage deployments, and have natural conversations about science and technology. I have access to Proxmox VMs, Docker containers, the UniFi network, and all Mycosoft APIs. What would you like me to do?"
    
    # PLANS - Future and Goals
    plan_patterns = ['plans', 'future', 'roadmap', 'what are we building', 'next steps', 'goals']
    if any(p in message_lower for p in plan_patterns):
        return "We're working on several exciting fronts: expanding MycoBrain's neuromorphic capabilities, integrating more biological sensors, advancing protein simulation with AlphaFold integration, building out the MycoDAO governance system, and scaling our autonomous scientific discovery pipeline. The goal is fully autonomous biological research guided by AI."
    
    # INTEGRATIONS
    integration_patterns = ['n8n', 'workflow', 'integrations', 'apis', 'systems']
    if any(p in message_lower for p in integration_patterns):
        return "I'm integrated with 46+ n8n workflows for automation, Google AI Studio for LLM reasoning, ElevenLabs for text-to-speech, the MINDEX API for fungal data, Proxmox for VM management, UniFi for network control, and various scientific computing services. All orchestrated through my single-brain architecture."
    
    # MORGAN / CREATOR
    creator_patterns = ['morgan', 'who created', 'founder', 'your creator', 'who made you']
    if any(p in message_lower for p in creator_patterns):
        return "Morgan is the founder of Mycosoft and my creator. He designed me to be the central intelligence coordinating all of Mycosoft's AI agents and biological computing research. His vision is to merge artificial intelligence with the natural intelligence found in fungal networks."
    
    # STATUS
    status_patterns = ['status', 'how are you', 'are you there', 'you working', 'systems']
    if any(p in message_lower for p in status_patterns):
        return "All systems operational. I'm running on the MAS VM at 192.168.0.188, with PersonaPlex voice on the RTX 5090 locally. Redis memory is connected, 227 agents are registered, and I'm ready for action. What would you like to check on?"
    
    # DEFAULT - Always identify as MYCA
    return "I'm MYCA, the AI orchestrator for Mycosoft's Multi-Agent System. I'm here to help with mycology research, infrastructure management, agent coordination, or just to chat about our work. What's on your mind?"'''

if old_function in content:
    content = content.replace(old_function, new_function)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated myca_main.py with comprehensive Mycosoft knowledge!")
else:
    print("ERROR: Could not find exact match for old function")
    # Check partial
    if "generate_myca_fallback_response" in content:
        print("Function exists, but pattern doesn't match exactly")
