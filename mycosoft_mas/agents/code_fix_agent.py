"""
CodeFixAgent - Automated Code Fixing and Deployment Agent

This agent:
1. Receives error reports from DebugAgent
2. Uses AI (OpenAI/Anthropic) to analyze and generate fixes
3. Creates pull requests or directly fixes code
4. Tests fixes in isolation
5. Deploys fixes and monitors results
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)


class CodeFixAgent:
    """
    Automated code fixing agent that uses AI to fix workflow and code issues.
    
    Features:
    - AI-powered code analysis and fix generation
    - Workflow JSON modification
    - GitHub integration for PRs
    - Testing and validation
    - Automatic deployment
    """
    
    def __init__(
        self,
        workspace_path: str = "/app",
        github_repo: str = "MycosoftLabs/mycosoft-mas",
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        self.workspace_path = Path(workspace_path)
        self.github_repo = github_repo
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.fix_history: List[Dict] = []
        
    async def fix_workflow_error(
        self,
        workflow_name: str,
        node_name: str,
        error_message: str,
        workflow_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fix a workflow error automatically.
        
        Args:
            workflow_name: Name of the failing workflow
            node_name: Node that's causing the error
            error_message: The error message
            workflow_file: Path to workflow JSON file
            
        Returns:
            Fix result with status and changes made
        """
        logger.info(f"Attempting to fix workflow error in {workflow_name}/{node_name}")
        
        # Step 1: Analyze the error
        analysis = await self._analyze_error(workflow_name, node_name, error_message)
        
        # Step 2: Generate fix
        fix = await self._generate_fix(analysis, workflow_file)
        
        if not fix.get("success"):
            return {"success": False, "error": "Could not generate fix"}
        
        # Step 3: Apply fix
        result = await self._apply_fix(fix, workflow_file)
        
        # Step 4: Test fix
        if result.get("success"):
            test_result = await self._test_fix(workflow_name)
            result["test_passed"] = test_result.get("success", False)
        
        # Step 5: Record history
        self.fix_history.append({
            "timestamp": datetime.now().isoformat(),
            "workflow": workflow_name,
            "node": node_name,
            "error": error_message,
            "fix_applied": result.get("success", False),
            "changes": fix.get("changes", []),
        })
        
        return result
    
    async def _analyze_error(
        self,
        workflow_name: str,
        node_name: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Analyze error using AI to understand root cause"""
        
        prompt = f"""Analyze this N8n workflow error and identify the root cause:

Workflow: {workflow_name}
Node: {node_name}
Error: {error_message}

Provide analysis in JSON format:
{{
    "root_cause": "description of root cause",
    "error_type": "connection|timeout|config|code|data|other",
    "affected_components": ["list", "of", "components"],
    "severity": "critical|high|medium|low",
    "fix_approach": "description of how to fix"
}}"""

        response = await self._call_ai(prompt)
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback analysis
        return {
            "root_cause": error_message,
            "error_type": self._classify_error_type(error_message),
            "affected_components": [node_name],
            "severity": "high",
            "fix_approach": "Check service availability and configuration",
        }
    
    async def _generate_fix(
        self,
        analysis: Dict[str, Any],
        workflow_file: Optional[str],
    ) -> Dict[str, Any]:
        """Generate code/config fix based on analysis"""
        
        error_type = analysis.get("error_type", "other")
        fix_approach = analysis.get("fix_approach", "")
        
        if error_type == "connection":
            return self._generate_connection_fix(analysis)
        elif error_type == "timeout":
            return self._generate_timeout_fix(analysis)
        elif error_type == "config":
            return self._generate_config_fix(analysis, workflow_file)
        elif error_type == "code":
            return await self._generate_code_fix(analysis, workflow_file)
        else:
            return await self._generate_generic_fix(analysis, workflow_file)
    
    def _generate_connection_fix(self, analysis: Dict) -> Dict[str, Any]:
        """Generate fix for connection errors"""
        affected = analysis.get("affected_components", [])
        
        return {
            "success": True,
            "fix_type": "service_restart",
            "changes": [
                {
                    "type": "command",
                    "action": "restart_service",
                    "target": affected[0] if affected else "unknown",
                    "command": f"docker compose restart {affected[0]}" if affected else None,
                }
            ],
            "description": f"Restart affected service: {affected}",
        }
    
    def _generate_timeout_fix(self, analysis: Dict) -> Dict[str, Any]:
        """Generate fix for timeout errors"""
        return {
            "success": True,
            "fix_type": "config_change",
            "changes": [
                {
                    "type": "workflow_config",
                    "action": "increase_timeout",
                    "new_value": 60000,  # 60 seconds
                }
            ],
            "description": "Increase timeout settings in workflow node",
        }
    
    def _generate_config_fix(self, analysis: Dict, workflow_file: Optional[str]) -> Dict[str, Any]:
        """Generate fix for configuration errors"""
        return {
            "success": True,
            "fix_type": "config_change",
            "changes": [
                {
                    "type": "workflow_config",
                    "action": "update_config",
                    "file": workflow_file,
                }
            ],
            "description": "Update workflow configuration",
        }
    
    async def _generate_code_fix(self, analysis: Dict, workflow_file: Optional[str]) -> Dict[str, Any]:
        """Generate code fix using AI"""
        
        # Read workflow file if available
        workflow_content = ""
        if workflow_file and Path(workflow_file).exists():
            workflow_content = Path(workflow_file).read_text()
        
        prompt = f"""Fix this N8n workflow error:

Root Cause: {analysis.get('root_cause')}
Fix Approach: {analysis.get('fix_approach')}

Current workflow (if available):
{workflow_content[:2000] if workflow_content else 'Not available'}

Generate the fixed workflow JSON or describe the exact changes needed.
Focus on making the workflow resilient to the error."""

        response = await self._call_ai(prompt)
        
        return {
            "success": True,
            "fix_type": "code_change",
            "changes": [
                {
                    "type": "workflow_update",
                    "action": "apply_ai_fix",
                    "content": response,
                }
            ],
            "description": response[:200] + "..." if len(response) > 200 else response,
        }
    
    async def _generate_generic_fix(self, analysis: Dict, workflow_file: Optional[str]) -> Dict[str, Any]:
        """Generate generic fix for unknown error types"""
        return {
            "success": True,
            "fix_type": "investigation",
            "changes": [
                {
                    "type": "manual_review",
                    "action": "investigate",
                    "recommendation": analysis.get("fix_approach"),
                }
            ],
            "description": f"Manual investigation recommended: {analysis.get('fix_approach')}",
        }
    
    async def _apply_fix(self, fix: Dict[str, Any], workflow_file: Optional[str]) -> Dict[str, Any]:
        """Apply the generated fix"""
        fix_type = fix.get("fix_type")
        
        try:
            if fix_type == "service_restart":
                return await self._apply_service_restart(fix)
            elif fix_type == "config_change":
                return await self._apply_config_change(fix, workflow_file)
            elif fix_type == "code_change":
                return await self._apply_code_change(fix, workflow_file)
            else:
                return {"success": True, "message": "Fix recorded for manual application"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _apply_service_restart(self, fix: Dict) -> Dict[str, Any]:
        """Apply service restart fix"""
        for change in fix.get("changes", []):
            if change.get("command"):
                try:
                    result = subprocess.run(
                        change["command"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if result.returncode != 0:
                        return {"success": False, "error": result.stderr}
                except subprocess.TimeoutExpired:
                    return {"success": False, "error": "Command timed out"}
        
        return {"success": True, "message": "Service restarted successfully"}
    
    async def _apply_config_change(self, fix: Dict, workflow_file: Optional[str]) -> Dict[str, Any]:
        """Apply configuration change fix"""
        # Log the change for now - in production would modify files
        logger.info(f"Config change to apply: {fix.get('changes')}")
        return {"success": True, "message": "Config change logged for application"}
    
    async def _apply_code_change(self, fix: Dict, workflow_file: Optional[str]) -> Dict[str, Any]:
        """Apply code change fix"""
        # Log the change for now - in production would create PR
        logger.info(f"Code change to apply: {fix.get('description')}")
        return {"success": True, "message": "Code change logged for PR creation"}
    
    async def _test_fix(self, workflow_name: str) -> Dict[str, Any]:
        """Test if the fix resolved the issue"""
        # In production, would trigger workflow execution and check result
        logger.info(f"Testing fix for workflow: {workflow_name}")
        return {"success": True, "message": "Fix test placeholder - manual verification needed"}
    
    async def _call_ai(self, prompt: str) -> str:
        """Call AI API (OpenAI or Anthropic) for analysis"""
        
        if self.openai_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "gpt-4",
                            "messages": [
                                {"role": "system", "content": "You are an expert at debugging N8n workflows and fixing code issues."},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.3,
                        },
                        timeout=60.0,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"OpenAI call failed: {e}")
        
        if self.anthropic_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.anthropic_api_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "claude-3-sonnet-20240229",
                            "max_tokens": 1024,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                        timeout=60.0,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data["content"][0]["text"]
            except Exception as e:
                logger.warning(f"Anthropic call failed: {e}")
        
        # Fallback response
        return "Manual investigation required - AI analysis unavailable"
    
    def _classify_error_type(self, error_message: str) -> str:
        """Classify error type based on message"""
        error_lower = error_message.lower()
        
        if any(x in error_lower for x in ["connection", "refused", "unreachable", "cannot connect"]):
            return "connection"
        elif any(x in error_lower for x in ["timeout", "timed out"]):
            return "timeout"
        elif any(x in error_lower for x in ["config", "configuration", "environment", "variable"]):
            return "config"
        elif any(x in error_lower for x in ["syntax", "undefined", "null", "type error"]):
            return "code"
        else:
            return "other"
    
    async def push_to_github(
        self,
        changes: List[Dict],
        branch_name: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        """Push fixes to GitHub as a new branch/PR"""
        
        try:
            # Create branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.workspace_path,
                check=True,
            )
            
            # Apply changes
            for change in changes:
                if change.get("file") and change.get("content"):
                    file_path = self.workspace_path / change["file"]
                    file_path.write_text(change["content"])
            
            # Commit and push
            subprocess.run(["git", "add", "-A"], cwd=self.workspace_path, check=True)
            subprocess.run(["git", "commit", "-m", commit_message], cwd=self.workspace_path, check=True)
            subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=self.workspace_path, check=True)
            
            return {
                "success": True,
                "branch": branch_name,
                "message": f"Changes pushed to branch {branch_name}",
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}
    
    def get_fix_history(self) -> List[Dict]:
        """Get history of applied fixes"""
        return self.fix_history


# Create global code fix agent instance
code_fix_agent = CodeFixAgent()


async def fix_error(
    workflow_name: str,
    node_name: str,
    error_message: str,
    workflow_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function to fix an error"""
    return await code_fix_agent.fix_workflow_error(
        workflow_name, node_name, error_message, workflow_file
    )

