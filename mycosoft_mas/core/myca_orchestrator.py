import asyncio
from fastapi import FastAPI, APIRouter, HTTPException
from langgraph.graph import Graph
from langgraph_mcp import MCPToolAdapter
from mycosoft_mas.services.voice_service import VoiceService
from mycosoft_mas.services.communication_service import CommunicationService
from mycosoft_mas.services.self_improvement import SelfImprovementService
from mycosoft_mas.services.observability import ObservabilityService
from mycosoft_mas.services.chat_service import ChatService
from mycosoft_mas.services.automation_service import AutomationService
import yaml
from pathlib import Path
import importlib
from typing import Dict, Any
from datetime import datetime
from mycosoft_mas.core.mcp_server import MCPServer
import logging

class MYCAOrchestrator:
    """
    MYCA is the central orchestrator for Mycosoft MAS, managing all agents, communication, and system evolution.
    """
    def __init__(self, config_path: str = "config/myca_personality.yaml", mcp_config_path: str = "config/mcp_servers.yaml"):
        self.config_path = config_path
        self.mcp_config_path = mcp_config_path
        self.personality = self._load_personality()
        self.voice_service = VoiceService(self.personality)
        self.communication_service = CommunicationService(self.personality)
        self.communication_service.set_voice_service(self.voice_service)
        self.self_improvement = SelfImprovementService(self)
        self.observability = ObservabilityService(self)
        self.graph = Graph()
        self.mcp_adapter = MCPToolAdapter(discover_all_servers=True)
        self.graph.use_tools(self.mcp_adapter)
        self.agents: Dict[str, Any] = {}
        self.app = FastAPI(title="MYCA Orchestrator")
        self.router = APIRouter()
        self.chat_service = ChatService()
        self.automation_service = AutomationService()
        self.mcp_servers: Dict[str, MCPServer] = {}
        self.tool_deployment_queue = asyncio.Queue()
        self.agent_update_queue = asyncio.Queue()
        self.deployment_workers = []
        self.update_workers = []
        self.deployment_status = {}
        self.update_status = {}
        self.logger = logging.getLogger("myca.orchestrator")
        self.security_tokens: Dict[str, str] = {}
        self.access_control: Dict[str, Dict[str, list]] = {}
        self.audit_log: list = []
        self.incident_logs: list = []
        self.vulnerability_scans: Dict[str, dict] = {}
        self.security_metrics: Dict[str, any] = {
            "total_alerts": 0,
            "critical_alerts": 0,
            "vulnerabilities_found": 0,
            "security_updates_applied": 0,
            "incidents_handled": 0,
            "last_scan": None
        }
        self.desktop_automation_agent = None
        self._load_mcp_servers()
        self._setup_routes()
        self._health_check_task = None
        self._load_desktop_automation()
        # Optionally auto-register agents on startup (stub for now)
        # self._auto_register_agents()

    def _load_personality(self):
        path = Path(self.config_path)
        if path.exists():
            with open(path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def _get_agent_class(self, class_name: str):
        """Dynamically import and return the agent class by name."""
        # Try all known agent modules
        agent_modules = [
            "mycosoft_mas.agents.research_agent",
            "mycosoft_mas.agents.project_management_agent",
            "mycosoft_mas.agents.desktop_automation_agent",
            "mycosoft_mas.agents.financial.financial_operations_agent",
            "mycosoft_mas.agents.corporate.board_operations_agent",
            "mycosoft_mas.agents.corporate.corporate_operations_agent",
            # Add more as needed
        ]
        for module_name in agent_modules:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    return getattr(module, class_name)
            except ImportError:
                continue
        raise ImportError(f"Agent class {class_name} not found in known modules.")

    def register_agent(self, agent_id, agent_node):
        # Inject MYCA as the orchestrator for notification routing
        if hasattr(agent_node, 'set_myca_orchestrator'):
            agent_node.set_myca_orchestrator(self)
        self.agents[agent_id] = agent_node
        self.graph.add_node(agent_id, node=agent_node)
        self.graph.add_edge("MYCA", agent_id)
        self.log_audit("register_agent", {"agent_id": agent_id})

    def remove_agent(self, agent_id):
        if agent_id in self.agents:
            self.graph.remove_node(agent_id)
            del self.agents[agent_id]
            self.log_audit("remove_agent", {"agent_id": agent_id})

    def command_agent(self, agent_id, command, **kwargs):
        agent = self.agents.get(agent_id)
        if agent:
            self.log_audit("command_agent", {"agent_id": agent_id, "command": command, "params": kwargs})
            return agent.handle_command(command, **kwargs)
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    def get_agent_status(self, agent_id):
        agent = self.agents.get(agent_id)
        if agent:
            return agent.get_status()
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    def list_agents(self):
        return list(self.agents.keys())

    def notify(self, message: str, channel: str = "dashboard", priority: str = "normal", agent_id: str = None, agent_name: str = None, event_type: str = None, context: dict = None):
        """
        Route a notification through MYCA's CommunicationService.
        Agents should call this method to send notifications (voice, text, dashboard, etc.).
        Supports rich context: agent_id, agent_name, event_type, context.
        """
        notification = {
            "message": message,
            "channel": channel,
            "priority": priority,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "event_type": event_type,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        # Stream to dashboard as well
        self.observability.stream_activity({"myca_notification": notification})
        return self.communication_service.notify(message, channel=channel, priority=priority)

    def _get_system_graph(self):
        """Return a dict representing the current system graph: nodes and edges."""
        nodes = []
        edges = []
        # Add MYCA node
        nodes.append({"id": "MYCA", "type": "orchestrator", "label": "MYCA Orchestrator"})
        # Add agent nodes
        for agent_id, agent in self.agents.items():
            nodes.append({"id": agent_id, "type": "agent", "label": getattr(agent, 'name', agent_id)})
            edges.append({"source": "MYCA", "target": agent_id, "type": "manages"})
        # Add service nodes
        service_nodes = [
            ("voice_service", self.voice_service),
            ("communication_service", self.communication_service),
            ("self_improvement", self.self_improvement),
            ("observability", self.observability),
            ("chat_service", self.chat_service),
            ("automation_service", self.automation_service),
        ]
        for sid, service in service_nodes:
            nodes.append({"id": sid, "type": "service", "label": sid.replace('_', ' ').title()})
            edges.append({"source": "MYCA", "target": sid, "type": "uses"})
        # Add tool nodes (from MCPToolAdapter if available)
        if hasattr(self, 'mcp_adapter') and hasattr(self.mcp_adapter, 'tools'):
            for tool in getattr(self.mcp_adapter, 'tools', []):
                tid = getattr(tool, 'id', str(tool))
                nodes.append({"id": tid, "type": "tool", "label": getattr(tool, 'name', tid)})
                edges.append({"source": "MYCA", "target": tid, "type": "integrates"})
        return {"nodes": nodes, "edges": edges}

    def _load_mcp_servers(self):
        path = Path(self.mcp_config_path)
        if not path.exists():
            return
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        for server_id, server_cfg in config.get("servers", {}).items():
            self.mcp_servers[server_id] = MCPServer(server_cfg)
        # Async init must be called after event loop starts

    async def initialize_mcp_servers(self):
        for server in self.mcp_servers.values():
            await server.initialize()

    def _load_agents(self, agents_config_path: str = "config/agents.yaml"):
        path = Path(agents_config_path)
        if not path.exists():
            return
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        for agent_id, agent_cfg in config.get("agents", {}).items():
            AgentClass = self._get_agent_class(agent_cfg["class"])
            agent = AgentClass(agent_id=agent_id, name=agent_cfg["name"], config=agent_cfg.get("config", {}))
            self.register_agent(agent_id, agent)

    def _load_modules(self, modules_config_path: str = "config/modules.yaml"):
        path = Path(modules_config_path)
        if not path.exists():
            return
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        self.modules = {}
        for mod_name, mod_cfg in config.get("modules", {}).items():
            try:
                module = importlib.import_module(mod_cfg["import_path"])
                if hasattr(module, "initialize"):
                    module.initialize(mod_cfg.get("config", {}))
                self.modules[mod_name] = module
            except Exception as e:
                print(f"Failed to load module {mod_name}: {e}")

    def _load_tools(self, tools_config_path: str = "config/tools.yaml"):
        path = Path(tools_config_path)
        if not path.exists():
            return
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        self.tools = {}
        for tool_name, tool_cfg in config.get("tools", {}).items():
            try:
                tool_module = importlib.import_module(tool_cfg["import_path"])
                tool_instance = tool_module.Tool(tool_cfg.get("config", {}))
                if hasattr(tool_instance, "initialize"):
                    tool_instance.initialize()
                self.tools[tool_name] = tool_instance
            except Exception as e:
                print(f"Failed to load tool {tool_name}: {e}")

    def reload_agents(self):
        self._load_agents()

    def reload_modules(self):
        self._load_modules()

    def reload_tools(self):
        self._load_tools()

    def _load_desktop_automation(self, config_path: str = "config/desktop_automation.yaml"):
        path = Path(config_path)
        if not path.exists():
            return
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        try:
            from mycosoft_mas.agents.desktop_automation_agent import DesktopAutomationAgent
            self.desktop_automation_agent = DesktopAutomationAgent(
                agent_id=config["agent_id"],
                name=config["name"],
                config=config.get("config", {})
            )
        except Exception as e:
            self.logger.error(f"Failed to load desktop automation agent: {e}")

    def route_message(self, message: dict):
        # message: {target_agent_id, type, ...}
        target_id = message.get("target_agent_id")
        msg_type = message.get("type")
        if target_id and target_id in self.agents:
            return self.agents[target_id].handle_message(message)
        elif self.desktop_automation_agent and msg_type in ["desktop", "browser"]:
            return self.desktop_automation_agent.handle_message(message)
        else:
            raise HTTPException(status_code=404, detail="No agent found for message routing")

    def _setup_routes(self):
        @self.router.post("/agent/create")
        async def create_agent(agent_type: str, agent_id: str, name: str, config: dict):
            """Create and register a new agent by type/class name."""
            try:
                AgentClass = self._get_agent_class(agent_type)
                agent = AgentClass(agent_id=agent_id, name=name, config=config)
                await agent.initialize()
                self.register_agent(agent_id, agent)
                return {"status": "success", "agent_id": agent_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post("/agent/{agent_id}/remove")
        async def remove_agent(agent_id: str):
            self.remove_agent(agent_id)
            return {"status": "removed", "agent_id": agent_id}

        @self.router.post("/agent/{agent_id}/command")
        async def command_agent(agent_id: str, command: str, params: dict = {}):
            return self.command_agent(agent_id, command, **params)

        @self.router.get("/agents")
        async def list_agents():
            return self.list_agents()

        @self.router.get("/agent/{agent_id}/status")
        async def agent_status(agent_id: str):
            return self.get_agent_status(agent_id)

        @self.router.post("/speak")
        async def speak(text: str):
            return self.voice_service.speak(text)

        @self.router.get("/status")
        async def status():
            return {"personality": self.personality, "agents": self.list_agents()}

        @self.router.post("/notify")
        async def notify_endpoint(payload: dict):
            """
            Agents can POST to this endpoint to send notifications to MYCA.
            Payload should include: message (str), channel (str), priority (str).
            """
            message = payload.get("message")
            channel = payload.get("channel", "dashboard")
            priority = payload.get("priority", "normal")
            return self.notify(message, channel, priority)

        @self.router.post("/api/voice")
        async def voice_api(payload: dict):
            text = payload.get("text")
            return self.voice_service.speak_api(text)

        @self.router.post("/api/chat")
        async def chat_api(payload: dict):
            message = payload.get("message")
            context = payload.get("context", {})
            response = self.chat_service.chat(message, context)
            return {"response": response}

        @self.router.post("/api/automation/zapier")
        async def zapier_api(payload: dict):
            event = payload.get("event")
            data = payload.get("data", {})
            self.automation_service.trigger_zapier(event, data)
            return {"status": "triggered"}

        @self.router.post("/api/automation/ifttt")
        async def ifttt_api(payload: dict):
            event = payload.get("event")
            data = payload.get("data", {})
            self.automation_service.trigger_ifttt(event, data)
            return {"status": "triggered"}

        @self.router.get("/api/graph")
        async def graph_api():
            """Return the current system graph as JSON."""
            return self._get_system_graph()

        @self.router.get("/mcp/servers")
        async def list_mcp_servers():
            return list(self.mcp_servers.keys())

        @self.router.get("/mcp/server/{server_id}/status")
        async def mcp_server_status(server_id: str):
            server = self.mcp_servers.get(server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            return {
                "is_healthy": server.is_healthy,
                "last_health_check": server.last_health_check,
                "metrics": server.metrics
            }

        @self.router.post("/mcp/server/{server_id}/command")
        async def mcp_server_command(server_id: str, command: str, params: dict = {}):
            server = self.mcp_servers.get(server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            return await server.execute_command(command, params)

        @self.router.post("/reload/agents")
        async def reload_agents_endpoint():
            self.reload_agents()
            return {"status": "reloaded"}

        @self.router.post("/reload/modules")
        async def reload_modules_endpoint():
            self.reload_modules()
            return {"status": "reloaded"}

        @self.router.post("/reload/tools")
        async def reload_tools_endpoint():
            self.reload_tools()
            return {"status": "reloaded"}

        @self.router.post("/deploy/tool")
        async def queue_tool_deployment(tool_id: str, server_id: str = "tool_integration", version: str = "latest"):
            deployment = {"tool_id": tool_id, "server_id": server_id, "version": version, "timestamp": datetime.now().isoformat()}
            await self.tool_deployment_queue.put(deployment)
            return {"status": "queued", "deployment": deployment}

        @self.router.post("/update/agent")
        async def queue_agent_update(agent_id: str, server_id: str = "primary", version: str = "latest"):
            update = {"agent_id": agent_id, "server_id": server_id, "version": version, "timestamp": datetime.now().isoformat()}
            await self.agent_update_queue.put(update)
            return {"status": "queued", "update": update}

        @self.router.get("/deploy/status/{tool_id}")
        async def get_deployment_status(tool_id: str):
            return self.deployment_status.get(tool_id, {"status": "unknown"})

        @self.router.get("/update/status/{agent_id}")
        async def get_update_status(agent_id: str):
            return self.update_status.get(agent_id, {"status": "unknown"})

        @self.router.get("/security/audit")
        async def get_audit_log():
            return self.audit_log[-100:]

        @self.router.get("/security/incidents")
        async def get_incidents():
            return self.incident_logs[-100:]

        @self.router.get("/security/vulnerabilities")
        async def get_vulnerabilities():
            return list(self.vulnerability_scans.values())[-100:]

        @self.router.get("/security/metrics")
        async def get_security_metrics():
            return self.security_metrics

        @self.router.post("/route-message")
        async def route_message_endpoint(payload: dict):
            return self.route_message(payload)

        self.app.include_router(self.router)

    async def start(self):
        # Start orchestrator, agents, and services
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._periodic_health_check())

    async def stop(self):
        # Graceful shutdown
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    async def _periodic_health_check(self):
        while True:
            for agent_id, agent in self.agents.items():
                try:
                    health = await agent.health_check()
                    self.observability.stream_activity({"agent_id": agent_id, "health": health})
                except Exception as e:
                    self.observability.stream_activity({"agent_id": agent_id, "health": False, "error": str(e)})
            await asyncio.sleep(30)

    async def start_workers(self, deployment_workers: int = 2, update_workers: int = 2):
        for i in range(deployment_workers):
            worker = asyncio.create_task(self._deployment_worker(f"deployment_worker_{i}"))
            self.deployment_workers.append(worker)
        for i in range(update_workers):
            worker = asyncio.create_task(self._update_worker(f"update_worker_{i}"))
            self.update_workers.append(worker)

    async def _deployment_worker(self, worker_id: str):
        while True:
            try:
                deployment = await self.tool_deployment_queue.get()
                await self._process_deployment(deployment)
                self.tool_deployment_queue.task_done()
            except Exception as e:
                self.logger.error(f"Deployment worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)

    async def _update_worker(self, worker_id: str):
        while True:
            try:
                update = await self.agent_update_queue.get()
                await self._process_agent_update(update)
                self.agent_update_queue.task_done()
            except Exception as e:
                self.logger.error(f"Update worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)

    async def _process_deployment(self, deployment: Dict[str, Any]):
        try:
            tool_id = deployment["tool_id"]
            server_id = deployment.get("server_id", "tool_integration")
            version = deployment.get("version", "latest")
            # Get tool and server
            tool = self.tools.get(tool_id)
            server = self.mcp_servers.get(server_id)
            if not tool or not server:
                raise ValueError(f"Tool {tool_id} or server {server_id} not found")
            # Prepare deployment package (stub)
            package = {"tool_id": tool_id, "version": version, "config": getattr(tool, "config", {}), "metadata": {"created_at": datetime.now().isoformat()}}
            # Deploy to MCP server
            result = await server.execute_command("deploy_tool", {"tool_id": tool_id, "package": package, "version": version})
            self.deployment_status[tool_id] = {"status": "deployed", "result": result, "timestamp": datetime.now().isoformat()}
            self.logger.info(f"Tool {tool_id} deployed successfully to {server_id}")
            return result
        except Exception as e:
            self.deployment_status[deployment["tool_id"]] = {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}
            self.logger.error(f"Deployment failed: {str(e)}")
            raise

    async def _process_agent_update(self, update: Dict[str, Any]):
        try:
            agent_id = update["agent_id"]
            server_id = update.get("server_id", "primary")
            version = update.get("version", "latest")
            # Get agent and server
            agent = self.agents.get(agent_id)
            server = self.mcp_servers.get(server_id)
            if not agent or not server:
                raise ValueError(f"Agent {agent_id} or server {server_id} not found")
            # Prepare update package (stub)
            package = {"agent_id": agent_id, "version": version, "config": getattr(agent, "config", {}), "metadata": {"created_at": datetime.now().isoformat()}}
            # Update via MCP server
            result = await server.execute_command("update_agent", {"agent_id": agent_id, "package": package, "version": version})
            self.update_status[agent_id] = {"status": "updated", "result": result, "timestamp": datetime.now().isoformat()}
            self.logger.info(f"Agent {agent_id} updated successfully via {server_id}")
            return result
        except Exception as e:
            self.update_status[update["agent_id"]] = {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}
            self.logger.error(f"Agent update failed: {str(e)}")
            raise

    def log_audit(self, action: str, detail: dict):
        entry = {
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat()
        }
        self.audit_log.append(entry)

    def log_incident(self, incident: dict):
        entry = {
            "incident": incident,
            "timestamp": datetime.now().isoformat()
        }
        self.incident_logs.append(entry)
        self.security_metrics["incidents_handled"] += 1

    def log_vulnerability(self, vuln: dict):
        self.vulnerability_scans[vuln["id"]] = vuln
        self.security_metrics["vulnerabilities_found"] += 1

    def check_access(self, token: str, resource: str, action: str) -> bool:
        # Stub: implement real access control
        return True

    # Example: wrap management actions with audit logging
    def register_agent(self, agent_id, agent_node):
        # ... existing code ...
        self.log_audit("register_agent", {"agent_id": agent_id})
        # ... existing code ...

    def remove_agent(self, agent_id):
        # ... existing code ...
        self.log_audit("remove_agent", {"agent_id": agent_id})
        # ... existing code ...

    def command_agent(self, agent_id, command, **kwargs):
        # ... existing code ...
        self.log_audit("command_agent", {"agent_id": agent_id, "command": command, "params": kwargs})
        # ... existing code ... 