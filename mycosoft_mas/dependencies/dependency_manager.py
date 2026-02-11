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
        """Add a dependency (in-memory by default; agent_id keeps old behavior)."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                self.agent_dependencies[agent_id] = {}
            self.agent_dependencies[agent_id][package] = version
            return self._resolve_agent_dependencies(agent_id)

        # Unit-test friendly: don't shell out; just record.
        self.dependencies[package] = version
        self.dependency_graph.setdefault(package, set())
        return {"status": "success"}
        
    def remove_dependency(self, package: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove a dependency (in-memory by default; agent_id keeps old behavior)."""
        if agent_id:
            if agent_id in self.agent_dependencies and package in self.agent_dependencies[agent_id]:
                del self.agent_dependencies[agent_id][package]
                return {"status": "success", "message": f"Dependency removed for agent {agent_id}"}
            return {"status": "error", "message": f"Dependency not found for agent {agent_id}"}
            
        self.dependencies.pop(package, None)
        self.dependency_graph.pop(package, None)
        for agent_deps in self.agent_dependencies.values():
            agent_deps.pop(package, None)
        return {"status": "success"}

    def add_dependency_relationship(self, package: str, required_package: str) -> None:
        self.dependency_graph.setdefault(package, set()).add(required_package)

    def remove_dependency_relationship(self, package: str, required_package: str) -> None:
        self.dependency_graph.setdefault(package, set()).discard(required_package)
        
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

        # Test contract: return a simple {package: version} mapping.
        result = subprocess.run(["poetry", "show"], capture_output=True, text=True)
        installed: Dict[str, str] = {}
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if not line or line.lower().startswith("package"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                installed[parts[0]] = parts[1]
        self.installed_versions = installed
        return installed
        
    def update_dependency(self, package: str, version: Optional[str] = None, 
                         agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Update a dependency to a specific version using Poetry."""
        if agent_id:
            if agent_id not in self.agent_dependencies:
                return {"status": "error", "message": f"Agent {agent_id} not found"}
            self.agent_dependencies[agent_id][package] = version
            return self._resolve_agent_dependencies(agent_id)
            
        # Test contract: always call `poetry update <package>`.
        result = subprocess.run(["poetry", "update", package], capture_output=True, text=True)
        if getattr(result, "returncode", 1) == 0:
            self.update_history.append({"package": package, "version": version, "timestamp": datetime.now(), "success": True})
            
            # Check for conflicts with agent dependencies
            for agent_id, agent_deps in self.agent_dependencies.items():
                if package in agent_deps and agent_deps[package] != version:
                    if package not in self.version_conflicts:
                        self.version_conflicts[package] = []
                    self.version_conflicts[package].append((agent_id, agent_deps[package]))
            return {"status": "success"}
        return {"status": "error"}

    def install_dependency(self, package: str, version: str) -> Dict[str, Any]:
        result = subprocess.run(["poetry", "add", f"{package}=={version}"], capture_output=True, text=True)
        if getattr(result, "returncode", 1) == 0:
            self.dependencies[package] = version
            return {"status": "success"}
        return {"status": "error"}

    def uninstall_dependency(self, package: str) -> Dict[str, Any]:
        result = subprocess.run(["poetry", "remove", package], capture_output=True, text=True)
        if getattr(result, "returncode", 1) == 0:
            self.dependencies.pop(package, None)
            return {"status": "success"}
        return {"status": "error"}
        
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
            
        # Test contract: parse a simple table "Package Current Latest" and return
        # {pkg: {current, latest}} with no wrapper.
        result = subprocess.run(["poetry", "show", "--outdated"], capture_output=True, text=True)
        updates: Dict[str, Dict[str, str]] = {}
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if not line or line.lower().startswith("package"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                updates[parts[0]] = {"current": parts[1], "latest": parts[2]}
        return updates
        
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
            
        result = subprocess.run(["poetry", "update"], capture_output=True, text=True)
        if getattr(result, "returncode", 1) == 0:
            self.update_history.append({"package": "all", "timestamp": datetime.now(), "success": True})
            return {"status": "success"}
        return {"status": "error"}
        
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
        return {
            "installed_dependencies": installed,
            "dependency_graph": {k: sorted(list(v)) for k, v in self.dependency_graph.items()},
            "update_history": list(self.update_history),
        }

    def resolve_dependencies(self) -> Set[str]:
        """Resolve dependency graph into a flat set of packages."""
        resolved: Set[str] = set()
        to_visit = list(self.dependency_graph.keys())
        while to_visit:
            pkg = to_visit.pop()
            if pkg in resolved:
                continue
            resolved.add(pkg)
            for req in self.dependency_graph.get(pkg, set()):
                to_visit.append(req)
        return resolved
        
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