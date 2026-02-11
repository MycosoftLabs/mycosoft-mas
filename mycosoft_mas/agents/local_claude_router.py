"""
Local Claude Code Router - Routes coding tasks to local dev machine.
Allows parallel execution: VM 187 + local machine working together.
Created: February 9, 2026
"""
import logging
import requests
from typing import Dict, Any, Optional, List
import asyncio

logger = logging.getLogger(__name__)


class LocalClaudeRouter:
    """Routes coding tasks to local Claude Code instances."""
    
    def __init__(self):
        self.local_instances: List[Dict[str, Any]] = []
        self.vm187_endpoint = "http://192.168.0.187:22"  # SSH to 187
        self.load_balancing = "round_robin"  # or "priority", "least_loaded"
        self.current_index = 0
        
    def register_local_instance(self, endpoint: str, capabilities: List[str], metadata: Dict[str, Any]):
        """Register a local Claude Code instance."""
        instance = {
            "endpoint": endpoint,
            "capabilities": capabilities,
            "metadata": metadata,
            "status": "available",
            "active_tasks": 0,
            "total_completed": 0
        }
        self.local_instances.append(instance)
        logger.info(f"Registered local Claude instance: {endpoint}")
        
    def get_available_instances(self) -> List[Dict[str, Any]]:
        """Get all available instances (local + VM187)."""
        instances = []
        
        # VM 187 (always available if SSH works)
        instances.append({
            "endpoint": self.vm187_endpoint,
            "type": "vm_ssh",
            "location": "vm_187",
            "capabilities": ["all"],
            "active_tasks": 0
        })
        
        # Local instances
        for instance in self.local_instances:
            if instance["status"] == "available":
                instance_copy = instance.copy()
                instance_copy["type"] = "local"
                instances.append(instance_copy)
                
        return instances
    
    async def route_task(
        self, 
        task_description: str, 
        repo: str = "mas",
        prefer_local: bool = False,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """
        Route a coding task to an available instance.
        
        Args:
            task_description: Task to execute
            repo: Repository (mas, website, mindex, etc.)
            prefer_local: Prefer local machine over VM 187
            parallel: Execute on multiple instances in parallel
            
        Returns:
            Result from Claude Code execution
        """
        available = self.get_available_instances()
        
        if not available:
            return {
                "status": "error",
                "message": "No Claude Code instances available"
            }
        
        # Parallel execution
        if parallel and len(available) > 1:
            return await self._execute_parallel(task_description, repo, available)
        
        # Single instance execution
        if prefer_local:
            local_instances = [i for i in available if i["type"] == "local"]
            if local_instances:
                return await self._execute_on_instance(local_instances[0], task_description, repo)
        
        # Default: round-robin or least loaded
        instance = self._select_instance(available)
        return await self._execute_on_instance(instance, task_description, repo)
    
    def _select_instance(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select instance using load balancing strategy."""
        if self.load_balancing == "round_robin":
            instance = instances[self.current_index % len(instances)]
            self.current_index += 1
            return instance
        elif self.load_balancing == "least_loaded":
            return min(instances, key=lambda x: x.get("active_tasks", 0))
        else:
            return instances[0]
    
    async def _execute_on_instance(
        self, 
        instance: Dict[str, Any], 
        task: str, 
        repo: str
    ) -> Dict[str, Any]:
        """Execute task on specific instance."""
        try:
            if instance["type"] == "vm_ssh":
                return await self._execute_vm_ssh(task, repo)
            elif instance["type"] == "local":
                return await self._execute_local(instance["endpoint"], task, repo)
            else:
                return {"status": "error", "message": f"Unknown instance type: {instance['type']}"}
        except Exception as e:
            logger.error(f"Execution failed on {instance.get('endpoint', 'unknown')}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_vm_ssh(self, task: str, repo: str) -> Dict[str, Any]:
        """Execute on VM 187 via SSH (existing MYCA method)."""
        # This calls the existing CodingAgent.invoke_claude_code method
        logger.info("Routing task to VM 187 via SSH")
        return {
            "status": "delegated",
            "message": "Task routed to VM 187 (use CodingAgent.invoke_claude_code)",
            "location": "vm_187"
        }
    
    async def _execute_local(self, endpoint: str, task: str, repo: str) -> Dict[str, Any]:
        """Execute on local machine via API."""
        logger.info(f"Routing task to local instance: {endpoint}")
        
        try:
            response = requests.post(
                f"{endpoint}/task",
                json={
                    "description": task,
                    "repo": repo,
                    "priority": 5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Task {result['id']} queued on local instance")
                
                # Poll for completion (async)
                return await self._poll_task_completion(endpoint, result["id"])
            else:
                return {
                    "status": "error",
                    "message": f"Local API returned {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to local instance: {endpoint}")
            return {
                "status": "error",
                "message": f"Connection failed: {endpoint}"
            }
    
    async def _poll_task_completion(self, endpoint: str, task_id: int, timeout: int = 600) -> Dict[str, Any]:
        """Poll local instance for task completion."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{endpoint}/task/{task_id}", timeout=5)
                
                if response.status_code == 200:
                    task = response.json()
                    
                    if task["status"] in ["completed", "failed"]:
                        return {
                            "status": task["status"],
                            "result": task.get("result"),
                            "location": "local",
                            "task_id": task_id
                        }
                
                # Wait before next poll
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)
        
        return {
            "status": "timeout",
            "message": f"Task {task_id} did not complete within {timeout}s"
        }
    
    async def _execute_parallel(
        self, 
        task: str, 
        repo: str, 
        instances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute task on multiple instances in parallel."""
        logger.info(f"Executing task on {len(instances)} instances in parallel")
        
        # Create tasks
        tasks = [
            self._execute_on_instance(instance, task, repo)
            for instance in instances
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return first successful result or aggregate
        successful = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
        
        if successful:
            return {
                "status": "completed",
                "results": successful,
                "parallel_execution": True,
                "instances_used": len(instances)
            }
        else:
            return {
                "status": "failed",
                "message": "All parallel executions failed",
                "errors": [str(r) for r in results]
            }


# Global router instance
_router = LocalClaudeRouter()


def get_router() -> LocalClaudeRouter:
    """Get global router instance."""
    return _router
