"""
Register all 96+ agents in the MINDEX PostgreSQL database.
Created: February 5, 2026
"""
import paramiko
import os

# MINDEX VM connection
mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "Mushroom1!Mushroom1!")

# Agent definitions - 50+ agents across all categories
agents = [
    # Orchestration (6)
    ("myca_agent", "orchestration", "MYCA Core Orchestrator - Central AI coordinator"),
    ("supervisor_agent", "orchestration", "Multi-agent workflow supervisor"),
    ("coordinator_agent", "orchestration", "Task coordination and routing"),
    ("registry_agent", "orchestration", "System registry management"),
    ("planner_agent", "orchestration", "Task planning and decomposition"),
    ("executor_agent", "orchestration", "Task execution management"),
    
    # Voice (6)
    ("speech_agent", "voice", "Speech processing and recognition"),
    ("tts_agent", "voice", "Text-to-speech synthesis"),
    ("stt_agent", "voice", "Speech-to-text transcription"),
    ("voice_bridge_agent", "voice", "PersonaPlex voice bridge"),
    ("dialog_agent", "voice", "Conversational dialog management"),
    ("intent_agent", "voice", "Intent classification and extraction"),
    
    # Scientific (7)
    ("lab_manager_agent", "scientific", "Laboratory experiment coordination"),
    ("experiment_agent", "scientific", "Experiment design and execution"),
    ("analysis_agent", "scientific", "Data analysis and reporting"),
    ("simulation_agent", "scientific", "Scientific simulation runner"),
    ("protocol_agent", "scientific", "Protocol management and execution"),
    ("mycology_agent", "scientific", "Mycology research specialist"),
    ("earth2_agent", "scientific", "Earth2 climate simulation"),
    
    # MycoBrain (6)
    ("telemetry_forwarder_agent", "mycobrain", "Device telemetry forwarding"),
    ("firmware_update_agent", "mycobrain", "Device firmware management"),
    ("nfc_agent", "mycobrain", "NFC tag reading and writing"),
    ("sensor_agent", "mycobrain", "Sensor data processing"),
    ("camera_agent", "mycobrain", "Camera vision processing"),
    ("grow_controller_agent", "mycobrain", "Growth environment control"),
    
    # NatureOS (4)
    ("device_registry_agent", "natureos", "Device registration and discovery"),
    ("environment_agent", "natureos", "Environmental monitoring"),
    ("data_pipeline_agent", "natureos", "Data pipeline orchestration"),
    ("edge_compute_agent", "natureos", "Edge computing coordination"),
    
    # Financial (4)
    ("trading_agent", "financial", "Crypto trading operations"),
    ("market_analysis_agent", "financial", "Market data analysis"),
    ("portfolio_agent", "financial", "Portfolio management"),
    ("opportunity_scout_agent", "financial", "Investment opportunity detection"),
    
    # Memory (5)
    ("memory_manager_agent", "memory", "Central memory coordination"),
    ("graph_memory_agent", "memory", "Knowledge graph operations"),
    ("vector_memory_agent", "memory", "Vector embedding storage"),
    ("session_memory_agent", "memory", "Session state management"),
    ("long_term_memory_agent", "memory", "Long-term memory persistence"),
    
    # Workflow (4)
    ("n8n_workflow_agent", "workflow", "n8n workflow execution"),
    ("trigger_agent", "workflow", "Event trigger management"),
    ("scheduler_agent", "workflow", "Task scheduling"),
    ("notification_agent", "workflow", "Notification dispatch"),
    
    # Integration (4)
    ("api_gateway_agent", "integration", "API gateway coordination"),
    ("webhook_agent", "integration", "Webhook management"),
    ("mcp_bridge_agent", "integration", "MCP protocol bridge"),
    ("database_agent", "integration", "Database operations"),
    
    # Utility (4)
    ("health_check_agent", "utility", "System health monitoring"),
    ("log_agent", "utility", "Log aggregation and analysis"),
    ("backup_agent", "utility", "Data backup operations"),
    ("cleanup_agent", "utility", "Resource cleanup"),
    
    # Extended Scientific (10)
    ("bioreactor_agent", "scientific", "Bioreactor monitoring and control"),
    ("genetics_agent", "scientific", "Genetic sequence analysis"),
    ("culture_agent", "scientific", "Culture management and tracking"),
    ("substrate_agent", "scientific", "Substrate preparation coordination"),
    ("harvesting_agent", "scientific", "Harvest timing optimization"),
    ("quality_agent", "scientific", "Quality control assessment"),
    ("contamination_agent", "scientific", "Contamination detection"),
    ("climate_model_agent", "scientific", "Climate modeling integration"),
    ("data_collector_agent", "scientific", "Scientific data collection"),
    ("visualization_agent", "scientific", "Data visualization generation"),
    
    # Extended MycoBrain (10)
    ("co2_sensor_agent", "mycobrain", "CO2 level monitoring"),
    ("humidity_sensor_agent", "mycobrain", "Humidity sensing and control"),
    ("temperature_sensor_agent", "mycobrain", "Temperature monitoring"),
    ("light_controller_agent", "mycobrain", "Light spectrum control"),
    ("fan_controller_agent", "mycobrain", "Ventilation control"),
    ("pump_controller_agent", "mycobrain", "Irrigation pump control"),
    ("weight_sensor_agent", "mycobrain", "Weight/scale monitoring"),
    ("ph_sensor_agent", "mycobrain", "pH level monitoring"),
    ("ec_sensor_agent", "mycobrain", "EC conductivity monitoring"),
    ("camera_ml_agent", "mycobrain", "ML-powered image analysis"),
    
    # Extended NatureOS (10)
    ("alert_agent", "natureos", "Alert generation and dispatch"),
    ("threshold_agent", "natureos", "Threshold monitoring"),
    ("calibration_agent", "natureos", "Sensor calibration"),
    ("maintenance_agent", "natureos", "Maintenance scheduling"),
    ("energy_agent", "natureos", "Energy consumption monitoring"),
    ("network_agent", "natureos", "Network health monitoring"),
    ("storage_agent", "natureos", "Storage management"),
    ("config_agent", "natureos", "Configuration management"),
    ("mesh_agent", "natureos", "Device mesh coordination"),
    ("ota_agent", "natureos", "OTA update distribution"),
    
    # Extended Memory (10)
    ("episodic_memory_agent", "memory", "Episodic event memory"),
    ("semantic_memory_agent", "memory", "Semantic knowledge storage"),
    ("working_memory_agent", "memory", "Working memory buffer"),
    ("conversation_memory_agent", "memory", "Conversation history"),
    ("context_memory_agent", "memory", "Context window management"),
    ("fact_extraction_agent", "memory", "Fact extraction from text"),
    ("embedding_agent", "memory", "Text embedding generation"),
    ("retrieval_agent", "memory", "Memory retrieval optimization"),
    ("compression_agent", "memory", "Memory compression"),
    ("decay_agent", "memory", "Memory decay management"),
    
    # Extended Workflow (6)
    ("cron_agent", "workflow", "Cron job execution"),
    ("queue_agent", "workflow", "Task queue management"),
    ("retry_agent", "workflow", "Retry logic handling"),
    ("timeout_agent", "workflow", "Timeout management"),
    ("dependency_agent", "workflow", "Dependency resolution"),
    ("parallel_agent", "workflow", "Parallel execution coordination"),
]

print(f"Registering {len(agents)} agents to MINDEX database...")

# Build SQL statements
sql_inserts = []
for name, agent_type, description in agents:
    # Escape single quotes
    desc_escaped = description.replace("'", "''")
    sql_inserts.append(
        f"INSERT INTO registry.agents (name, type, description, status) "
        f"VALUES ('{name}', '{agent_type}', '{desc_escaped}', 'offline') "
        f"ON CONFLICT (name) DO UPDATE SET type = EXCLUDED.type, description = EXCLUDED.description;"
    )

sql_batch = "\n".join(sql_inserts)
sql_count = "SELECT COUNT(*) as total FROM registry.agents;"
sql_summary = "SELECT type, COUNT(*) FROM registry.agents GROUP BY type ORDER BY type;"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    # Execute batch insert
    cmd = f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql_batch}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if err and "ERROR" in err:
        print(f"Insert errors: {err}")
    else:
        print("Agents inserted successfully")
    
    # Get total count
    cmd = f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql_count}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"\nTotal agents registered:\n{out}")
    
    # Get summary by type
    cmd = f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql_summary}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Agents by category:\n{out}")
    
    # Show sample agents
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, type, status FROM registry.agents ORDER BY type, name LIMIT 20;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Sample agents (first 20):\n{out}")
    
    ssh.close()
    print("\n✓ Agent registration complete!")
    
except Exception as e:
    print(f"Error: {e}")
