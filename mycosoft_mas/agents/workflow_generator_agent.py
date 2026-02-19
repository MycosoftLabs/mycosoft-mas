"""
Workflow Generator Agent for MYCA Voice System
Created: February 4, 2026

Agent that dynamically creates n8n workflows based on
natural language descriptions and requirements.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class WorkflowNode:
    """A node in an n8n workflow."""
    node_id: str
    name: str
    node_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    position: tuple = (0, 0)
    
    def to_n8n_format(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "typeVersion": 1,
            "position": list(self.position),
            "parameters": self.parameters,
        }


@dataclass
class WorkflowConnection:
    """A connection between nodes."""
    from_node: str
    to_node: str
    from_output: int = 0
    to_input: int = 0


@dataclass
class GeneratedWorkflow:
    """A generated n8n workflow."""
    workflow_id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    connections: List[WorkflowConnection]
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_n8n_format(self) -> Dict[str, Any]:
        """Convert to n8n workflow JSON format."""
        # Build connections dict
        conn_dict = {}
        for conn in self.connections:
            if conn.from_node not in conn_dict:
                conn_dict[conn.from_node] = {"main": [[]]}
            conn_dict[conn.from_node]["main"][0].append({
                "node": conn.to_node,
                "type": "main",
                "index": conn.to_input,
            })
        
        return {
            "name": self.name,
            "nodes": [n.to_n8n_format() for n in self.nodes],
            "connections": conn_dict,
            "settings": {"executionOrder": "v1"},
            "tags": self.tags,
        }


class WorkflowGeneratorAgent:
    """
    Agent that generates n8n workflows dynamically.
    
    Features:
    - Natural language to workflow conversion
    - Template-based workflow generation
    - Workflow validation
    - Direct deployment to n8n
    """
    
    # Common node templates
    NODE_TEMPLATES = {
        "webhook": {
            "type": "n8n-nodes-base.webhook",
            "params": {"httpMethod": "POST", "responseMode": "responseNode"}
        },
        "http_request": {
            "type": "n8n-nodes-base.httpRequest",
            "params": {"method": "POST"}
        },
        "if": {
            "type": "n8n-nodes-base.if",
            "params": {}
        },
        "switch": {
            "type": "n8n-nodes-base.switch",
            "params": {}
        },
        "set": {
            "type": "n8n-nodes-base.set",
            "params": {}
        },
        "respond": {
            "type": "n8n-nodes-base.respondToWebhook",
            "params": {"respondWith": "json"}
        },
        "code": {
            "type": "n8n-nodes-base.code",
            "params": {"language": "javaScript"}
        },
    }
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        n8n_api_url: str = "http://n8n:5678",
        n8n_api_key: Optional[str] = None,
    ):
        self.llm_client = llm_client
        self.n8n_api_url = n8n_api_url
        self.n8n_api_key = n8n_api_key
        
        self.generated_workflows: Dict[str, GeneratedWorkflow] = {}
        
        logger.info("WorkflowGeneratorAgent initialized")
    
    async def generate_workflow(
        self,
        description: str,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> GeneratedWorkflow:
        """
        Generate a workflow from natural language description.
        
        Args:
            description: Natural language workflow description
            name: Optional workflow name
            tags: Optional tags
            
        Returns:
            Generated workflow
        """
        logger.info(f"Generating workflow: {description}")
        
        # Generate workflow structure using LLM or templates
        if self.llm_client:
            workflow_spec = await self._llm_generate_spec(description)
        else:
            workflow_spec = self._template_generate_spec(description)
        
        workflow_id = hashlib.md5(f"{description}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Build nodes
        nodes = []
        for i, node_spec in enumerate(workflow_spec.get("nodes", [])):
            node = WorkflowNode(
                node_id=f"node_{i}",
                name=node_spec.get("name", f"Node {i}"),
                node_type=node_spec.get("type", "n8n-nodes-base.set"),
                parameters=node_spec.get("parameters", {}),
                position=(250 + i * 200, 300),
            )
            nodes.append(node)
        
        # Build connections
        connections = []
        for conn_spec in workflow_spec.get("connections", []):
            connections.append(WorkflowConnection(
                from_node=conn_spec.get("from"),
                to_node=conn_spec.get("to"),
            ))
        
        workflow = GeneratedWorkflow(
            workflow_id=workflow_id,
            name=name or workflow_spec.get("name", f"Generated: {description[:30]}"),
            description=description,
            nodes=nodes,
            connections=connections,
            tags=tags or ["generated", "voice"],
        )
        
        self.generated_workflows[workflow_id] = workflow
        
        logger.info(f"Generated workflow: {workflow_id} with {len(nodes)} nodes")
        return workflow
    
    async def _llm_generate_spec(self, description: str) -> Dict[str, Any]:
        """Use LLM to generate workflow specification."""
        prompt = f"""Generate an n8n workflow specification for:

{description}

Provide JSON with:
{{
    "name": "workflow name",
    "nodes": [
        {{"name": "node name", "type": "n8n-nodes-base.xxx", "parameters": {{}}}}
    ],
    "connections": [
        {{"from": "node_0", "to": "node_1"}}
    ]
}}

Use these node types:
- n8n-nodes-base.webhook (for triggers)
- n8n-nodes-base.httpRequest (for API calls)
- n8n-nodes-base.if (for conditions)
- n8n-nodes-base.set (for data transformation)
- n8n-nodes-base.respondToWebhook (for responses)
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return self._template_generate_spec(description)
    
    def _template_generate_spec(self, description: str) -> Dict[str, Any]:
        """Generate workflow using templates."""
        desc_lower = description.lower()
        
        # Determine workflow type from description
        if "api" in desc_lower or "webhook" in desc_lower:
            return self._api_workflow_template(description)
        elif "notify" in desc_lower or "alert" in desc_lower:
            return self._notification_workflow_template(description)
        elif "process" in desc_lower or "transform" in desc_lower:
            return self._processing_workflow_template(description)
        else:
            return self._basic_workflow_template(description)
    
    def _api_workflow_template(self, description: str) -> Dict[str, Any]:
        """Template for API workflows."""
        return {
            "name": f"API: {description[:30]}",
            "nodes": [
                {"name": "Webhook", "type": "n8n-nodes-base.webhook", "parameters": {"httpMethod": "POST", "path": "generated-api"}},
                {"name": "Process", "type": "n8n-nodes-base.code", "parameters": {"jsCode": "// Process request"}},
                {"name": "Respond", "type": "n8n-nodes-base.respondToWebhook", "parameters": {"respondWith": "json"}},
            ],
            "connections": [
                {"from": "Webhook", "to": "Process"},
                {"from": "Process", "to": "Respond"},
            ],
        }
    
    def _notification_workflow_template(self, description: str) -> Dict[str, Any]:
        """Template for notification workflows."""
        return {
            "name": f"Notify: {description[:30]}",
            "nodes": [
                {"name": "Trigger", "type": "n8n-nodes-base.webhook", "parameters": {"httpMethod": "POST", "path": "notify"}},
                {"name": "Format Message", "type": "n8n-nodes-base.set", "parameters": {}},
                {"name": "Send Notification", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": "http://personaplex-bridge:8999/api/announce"}},
                {"name": "Respond", "type": "n8n-nodes-base.respondToWebhook", "parameters": {}},
            ],
            "connections": [
                {"from": "Trigger", "to": "Format Message"},
                {"from": "Format Message", "to": "Send Notification"},
                {"from": "Send Notification", "to": "Respond"},
            ],
        }
    
    def _processing_workflow_template(self, description: str) -> Dict[str, Any]:
        """Template for data processing workflows."""
        return {
            "name": f"Process: {description[:30]}",
            "nodes": [
                {"name": "Input", "type": "n8n-nodes-base.webhook", "parameters": {"httpMethod": "POST", "path": "process"}},
                {"name": "Validate", "type": "n8n-nodes-base.if", "parameters": {}},
                {"name": "Transform", "type": "n8n-nodes-base.code", "parameters": {}},
                {"name": "Output", "type": "n8n-nodes-base.respondToWebhook", "parameters": {}},
            ],
            "connections": [
                {"from": "Input", "to": "Validate"},
                {"from": "Validate", "to": "Transform"},
                {"from": "Transform", "to": "Output"},
            ],
        }
    
    def _basic_workflow_template(self, description: str) -> Dict[str, Any]:
        """Basic workflow template."""
        return {
            "name": f"Workflow: {description[:30]}",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.webhook", "parameters": {"httpMethod": "POST", "path": "start"}},
                {"name": "Execute", "type": "n8n-nodes-base.code", "parameters": {}},
                {"name": "End", "type": "n8n-nodes-base.respondToWebhook", "parameters": {}},
            ],
            "connections": [
                {"from": "Start", "to": "Execute"},
                {"from": "Execute", "to": "End"},
            ],
        }
    
    async def deploy_workflow(self, workflow: GeneratedWorkflow) -> Dict[str, Any]:
        """Deploy a workflow to n8n."""
        import aiohttp
        
        workflow_json = workflow.to_n8n_format()
        
        headers = {"Content-Type": "application/json"}
        if self.n8n_api_key:
            headers["X-N8N-API-KEY"] = self.n8n_api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.n8n_api_url}/api/v1/workflows",
                    json=workflow_json,
                    headers=headers,
                ) as response:
                    result = await response.json()
                    logger.info(f"Deployed workflow: {workflow.workflow_id}")
                    return result
        except Exception as e:
            logger.error(f"Failed to deploy workflow: {e}")
            return {"error": str(e)}
    
    def get_workflow(self, workflow_id: str) -> Optional[GeneratedWorkflow]:
        """Get a generated workflow."""
        return self.generated_workflows.get(workflow_id)
    
    def export_workflow(self, workflow_id: str) -> Optional[str]:
        """Export workflow as JSON string."""
        workflow = self.get_workflow(workflow_id)
        if workflow:
            return json.dumps(workflow.to_n8n_format(), indent=2)
        return None


# Singleton
_agent_instance: Optional[WorkflowGeneratorAgent] = None


def get_workflow_generator() -> WorkflowGeneratorAgent:
    global _agent_instance
    if _agent_instance is None:
        n8n_url = os.getenv("N8N_URL", "http://192.168.0.188:5678")
        n8n_key = os.getenv("N8N_API_KEY", "")
        _agent_instance = WorkflowGeneratorAgent(n8n_api_url=n8n_url, n8n_api_key=n8n_key)
    return _agent_instance


async def generate_save_and_sync_workflow(
    description: str,
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a workflow from description, save to n8n/workflows/, and trigger sync-both.
    Returns dict with workflow_id, name, file_path, sync_result.
    """
    from mycosoft_mas.core.n8n_workflow_engine import WORKFLOWS_DIR, N8NWorkflowEngine

    generator = get_workflow_generator()
    workflow = await generator.generate_workflow(description=description, name=name, tags=tags)
    safe_name = "".join(c if c.isalnum() or c in " ._-" else "_" for c in workflow.name).strip().replace(" ", "_")
    if not safe_name:
        safe_name = f"generated_{workflow.workflow_id}"
    file_path = Path(WORKFLOWS_DIR) / f"{safe_name}.json"
    workflow_json = workflow.to_n8n_format()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(workflow_json, f, indent=2)
    logger.info(f"Saved generated workflow to {file_path}")

    engine = N8NWorkflowEngine()
    sync_result = await asyncio.to_thread(engine.sync_all_local_workflows, True)
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "file_path": str(file_path),
        "sync": {
            "imported": sync_result.imported,
            "skipped": sync_result.skipped,
            "errors": sync_result.errors,
        },
    }


__all__ = [
    "WorkflowGeneratorAgent",
    "GeneratedWorkflow",
    "WorkflowNode",
    "WorkflowConnection",
    "get_workflow_generator",
    "generate_save_and_sync_workflow",
]
