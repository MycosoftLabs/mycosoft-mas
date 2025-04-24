#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

class MASCleanup:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.mas_dir = self.root_dir / "mycosoft_mas"
        
        # Define required directory structure
        self.required_dirs = {
            "mycosoft_mas": {
                "agents": ["base_agent.py", "messaging/", "README.md"],
                "core": ["knowledge_graph.py", "myca_main.py", "README.md"],
                "services": ["evolution_monitor.py", "security_monitor.py", "technology_tracker.py", "README.md"],
                "integrations": ["integration_manager.py", "README.md"],
                "dependencies": ["dependency_manager.py", "README.md"],
                "monitoring": ["dashboard.py", "metrics.py", "README.md"],
                "config": ["config.yaml", "README.md"],
                "tests": ["test_agents/", "test_services/", "test_integrations/", "README.md"],
                "docs": ["architecture.md", "protocols.md", "metrics.md", "README.md"],
                "scripts": ["cleanup_mas.py", "README.md"],
                "data": ["README.md"],
                "logs": ["README.md"]
            }
        }
        
        # Define files/directories to remove (only truly unnecessary cache files)
        self.to_remove = [
            "__pycache__",  # Python cache files
            ".pytest_cache",  # Test cache
            "htmlcov"  # Test coverage reports
        ]
        
        # Define files to move to logs directory
        self.logs_to_move = {
            "dashboard.log": "mycosoft_mas/logs/dashboard.log",
            "agent_manager.log": "mycosoft_mas/logs/agent_manager.log",
            "project_management_agent.log": "mycosoft_mas/logs/project_management_agent.log",
            "finance_admin_agent.log": "mycosoft_mas/logs/finance_admin_agent.log"
        }

    def check_structure(self):
        """Check if the current structure matches the required structure."""
        issues = []
        
        # Check required directories
        for dir_path, files in self.required_dirs["mycosoft_mas"].items():
            full_path = self.mas_dir / dir_path
            if not full_path.exists():
                issues.append(f"Missing directory: {dir_path}")
                continue
                
            for file in files:
                if not (full_path / file).exists():
                    issues.append(f"Missing file: {dir_path}/{file}")
        
        # Check for unnecessary cache files/directories
        for item in self.to_remove:
            if (self.root_dir / item).exists():
                issues.append(f"Cache file/directory found: {item}")
        
        # Check for logs in wrong location
        for log_file, _ in self.logs_to_move.items():
            if (self.root_dir / log_file).exists():
                issues.append(f"Log file found in root directory: {log_file}")
        
        return issues

    def cleanup(self):
        """Perform cleanup operations."""
        print("Starting cleanup...")
        
        # Remove cache files/directories
        for item in self.to_remove:
            path = self.root_dir / item
            if path.exists():
                if path.is_file():
                    path.unlink()
                    print(f"Removed cache file: {item}")
                else:
                    shutil.rmtree(path)
                    print(f"Removed cache directory: {item}")
        
        # Move log files to logs directory
        for source, target in self.logs_to_move.items():
            source_path = self.root_dir / source
            target_path = self.root_dir / target
            
            if source_path.exists():
                # Ensure target directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the file
                shutil.move(str(source_path), str(target_path))
                print(f"Moved log file: {source} -> {target}")
        
        # Create missing directories and files
        for dir_path, files in self.required_dirs["mycosoft_mas"].items():
            full_path = self.mas_dir / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True)
                print(f"Created directory: {dir_path}")
            
            for file in files:
                if not (full_path / file).exists():
                    if file.endswith(".py"):
                        (full_path / file).touch()
                    elif file == "README.md":
                        with open(full_path / file, "w") as f:
                            f.write(f"# {dir_path.title()} Documentation\n\n")
                    print(f"Created file: {dir_path}/{file}")
        
        print("Cleanup completed!")

    def run(self):
        """Run the cleanup process."""
        issues = self.check_structure()
        
        if issues:
            print("Found the following issues:")
            for issue in issues:
                print(f"- {issue}")
            
            response = input("\nDo you want to proceed with cleanup? (y/n): ")
            if response.lower() == 'y':
                self.cleanup()
            else:
                print("Cleanup aborted.")
        else:
            print("No issues found. Structure is clean!")

if __name__ == "__main__":
    cleanup = MASCleanup()
    cleanup.run() 