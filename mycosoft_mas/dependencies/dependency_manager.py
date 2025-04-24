from typing import Dict, List, Any, Set, Optional, Tuple
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from packaging.version import parse as parse_version

class DependencyManager:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dependencies: Dict[str, str] = {}  # package -> version
        self.agent_dependencies: Dict[str, Dict[str, str]] = {}  # agent_id -> {package -> version}
        self.dependency_graph: Dict[str, Set[str]] = {}  # package -> required packages
        self.installed_versions: Dict[str, str] = {}  # package -> installed version
        self.update_history: List[Dict[str, Any]] = []
        self.version_conflicts: Dict[str, List[Tuple[str, str]]] = {}  # package -> [(agent_id, version)]
        self.logger = logging.getLogger(__name__)
        
    def _run_poetry_command(self, command: List[str], capture_output: bool = True) -> Dict[str, Any]:
        """Run a Poetry command and handle the output."""
        try:
            result = subprocess.run(
                ["poetry"] + command,
                cwd=str(self.project_root),
                capture_output=capture_output,
                text=True,
                check=True
            )
            return {
                "status": "success",
                "output": result.stdout if capture_output else None,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Poetry command failed: {e.stderr}")
            return {
                "status": "error",
                "output": e.stdout if capture_output else None,
                "error": e.stderr
            }
            
    def register_agent_dependencies(self, agent_id: str, dependencies: Dict[str, str]) -> Dict[str, Any]:
        """Register dependencies for a specific agent."""
        self.agent_dependencies[agent_id] = dependencies
        return self._resolve_agent_dependencies(agent_id)
        
    def _resolve_agent_dependencies(self, agent_id: str) -> Dict[str, Any]:
        """Resolve dependencies for a specific agent, checking for conflicts."""
        agent_deps = self.agent_dependencies[agent_id]
        conflicts = {}
        
        for package, version in agent_deps.items():
            if package in self.dependencies:
                current_version = self.dependencies[package]
                if current_version != version:
                    if package not in self.version_conflicts:
                        self.version_conflicts[package] = []
                    self.version_conflicts[package].append((agent_id, version))
                    conflicts[package] = {
                        "current": current_version,
                        "requested": version
                    }
                    
        if conflicts:
            self.logger.warning(f"Version conflicts found for agent {agent_id}: {conflicts}")
            return {
                "status": "conflict",
                "conflicts": conflicts,
                "message": "Version conflicts detected"
            }
            
        return {
            "status": "success",
            "message": "Dependencies registered successfully"
        }
        
    def add_dependency(self, package: str, version: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a dependency with its version using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                self.agent_dependencies[agent_id] = {}
            self.agent_dependencies[agent_id][package] = version
            return self._resolve_agent_dependencies(agent_id)
            
        result = self._run_poetry_command(["add", f"{package}=={version}"])
        if result["status"] == "success":
            self.dependencies[package] = version
            if package not in self.dependency_graph:
                self.dependency_graph[package] = set()
                
            # Check for conflicts with agent-specific dependencies
            for agent_id, agent_deps in self.agent_dependencies.items():
                if package in agent_deps and agent_deps[package] != version:
                    if package not in self.version_conflicts:
                        self.version_conflicts[package] = []
                    self.version_conflicts[package].append((agent_id, agent_deps[package]))
                    
        return result
        
    def remove_dependency(self, package: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove a dependency using Poetry."""
        if agent_id:
            if agent_id in self.agent_dependencies and package in self.agent_dependencies[agent_id]:
                del self.agent_dependencies[agent_id][package]
                return {"status": "success", "message": f"Dependency removed for agent {agent_id}"}
            return {"status": "error", "message": f"Dependency not found for agent {agent_id}"}
            
        result = self._run_poetry_command(["remove", package])
        if result["status"] == "success":
            self.dependencies.pop(package, None)
            self.dependency_graph.pop(package, None)
            
            # Remove from agent dependencies if present
            for agent_deps in self.agent_dependencies.values():
                agent_deps.pop(package, None)
                
        return result
        
    def check_dependencies(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Check installed dependencies and their versions using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            return {
                "status": "success",
                "dependencies": self.agent_dependencies[agent_id],
                "conflicts": {
                    package: versions for package, versions in self.version_conflicts.items()
                    if any(agent == agent_id for agent, _ in versions)
                }
            }
            
        result = self._run_poetry_command(["show", "--no-dev", "--outdated"])
        if result["status"] == "success":
            installed = {}
            for line in result["output"].split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        installed[parts[0]] = parts[1]
            self.installed_versions = installed
            return {
                "status": "success",
                "dependencies": installed,
                "conflicts": self.version_conflicts
            }
        return {"status": "error", "message": "Failed to check dependencies"}
        
    def update_dependency(self, package: str, version: Optional[str] = None, 
                         agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Update a dependency to a specific version using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            self.agent_dependencies[agent_id][package] = version
            return self._resolve_agent_dependencies(agent_id)
            
        if version:
            result = self._run_poetry_command(["add", f"{package}=={version}"])
        else:
            result = self._run_poetry_command(["update", package])
            
        if result["status"] == "success":
            self.update_history.append({
                "package": package,
                "version": version,
                "timestamp": datetime.now(),
                "success": True
            })
            
            # Check for conflicts with agent dependencies
            for agent_id, agent_deps in self.agent_dependencies.items():
                if package in agent_deps and agent_deps[package] != version:
                    if package not in self.version_conflicts:
                        self.version_conflicts[package] = []
                    self.version_conflicts[package].append((agent_id, agent_deps[package]))
                    
        return result
        
    def install_dependencies(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Install dependencies using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            agent_deps = self.agent_dependencies[agent_id]
            for package, version in agent_deps.items():
                result = self._run_poetry_command(["add", f"{package}=={version}"])
                if result["status"] != "success":
                    return result
            return {"status": "success", "message": f"Dependencies installed for agent {agent_id}"}
            
        result = self._run_poetry_command(["install"])
        if result["status"] == "success":
            self.update_history.append({
                "package": "all",
                "timestamp": datetime.now(),
                "success": True
            })
        return result
        
    def check_for_updates(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Check for available updates using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            agent_deps = self.agent_dependencies[agent_id]
            updates = {}
            for package, version in agent_deps.items():
                result = self._run_poetry_command(["show", package, "--outdated"])
                if result["status"] == "success" and result["output"]:
                    parts = result["output"].split()
                    if len(parts) >= 3:
                        updates[package] = {
                            "current": parts[1],
                            "latest": parts[2]
                        }
            return {"status": "success", "updates": updates}
            
        result = self._run_poetry_command(["show", "--outdated"])
        updates = {}
        if result["status"] == "success":
            for line in result["output"].split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 3:
                        updates[parts[0]] = {
                            "current": parts[1],
                            "latest": parts[2]
                        }
        return {"status": "success", "updates": updates}
        
    def update_all_dependencies(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Update all dependencies using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            agent_deps = self.agent_dependencies[agent_id]
            for package, version in agent_deps.items():
                result = self.update_dependency(package, version, agent_id)
                if result["status"] != "success":
                    return result
            return {"status": "success", "message": f"Dependencies updated for agent {agent_id}"}
            
        result = self._run_poetry_command(["update"])
        if result["status"] == "success":
            self.update_history.append({
                "package": "all",
                "timestamp": datetime.now(),
                "success": True
            })
        return result
        
    def generate_dependency_report(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a comprehensive dependency report using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            return {
                "agent_id": agent_id,
                "dependencies": self.agent_dependencies[agent_id],
                "conflicts": {
                    package: versions for package, versions in self.version_conflicts.items()
                    if any(agent == agent_id for agent, _ in versions)
                }
            }
            
        installed = self.check_dependencies()
        updates = self.check_for_updates()
        
        # Get Poetry environment info
        env_result = self._run_poetry_command(["env", "info", "--json"])
        env_info = json.loads(env_result["output"]) if env_result["status"] == "success" else {}
        
        return {
            "installed_dependencies": installed,
            "available_updates": updates,
            "dependency_graph": self.dependency_graph,
            "update_history": self.update_history,
            "environment": env_info,
            "agent_dependencies": self.agent_dependencies,
            "version_conflicts": self.version_conflicts
        }
        
    def resolve_version_conflicts(self) -> Dict[str, Any]:
        """Attempt to resolve version conflicts by finding compatible versions."""
        resolutions = {}
        for package, conflicts in self.version_conflicts.items():
            versions = [version for _, version in conflicts]
            versions.append(self.dependencies.get(package))
            
            # Try to find a compatible version
            compatible_version = self._find_compatible_version(package, versions)
            if compatible_version:
                resolutions[package] = compatible_version
                
        return resolutions
        
    def _find_compatible_version(self, package: str, versions: List[str]) -> Optional[str]:
        """Find a compatible version that satisfies all requirements."""
        if not versions:
            return None
            
        # Sort versions and try the latest one that satisfies all requirements
        sorted_versions = sorted(versions, key=parse_version, reverse=True)
        for version in sorted_versions:
            try:
                result = self._run_poetry_command(["add", f"{package}=={version}"])
                if result["status"] == "success":
                    return version
            except Exception:
                continue
        return None 