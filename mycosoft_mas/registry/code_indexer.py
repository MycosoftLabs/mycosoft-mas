"""
Code Indexer - February 4, 2026

Indexes all source code files across Mycosoft repositories,
extracting class definitions, function signatures, imports,
and exports for the system registry.

Repositories:
- MAS: mycosoft-mas (Python)
- Website: website (TypeScript/TSX)
- NatureOS: NatureOS (C#)
- MINDEX: mindex (Python)
- NLM: nlm (Python)
- MycoBrain: mycobrain (C++/Arduino)
"""

import os
import re
import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mycosoft_mas.registry.system_registry import (
    get_registry, SystemRegistry, CodeFileInfo
)

logger = logging.getLogger("CodeIndexer")


# ============================================================================
# Repository Configuration
# ============================================================================

REPO_CONFIGS = {
    "mas": {
        "path": os.getenv("MAS_REPO_PATH", "/home/mycosoft/mycosoft-mas"),
        "extensions": [".py"],
        "exclude_dirs": ["__pycache__", ".git", "node_modules", ".venv", "venv", 
                         ".pytest_cache", ".mypy_cache", "models", "data"],
    },
    "website": {
        "path": os.getenv("WEBSITE_REPO_PATH", "/home/mycosoft/website"),
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
        "exclude_dirs": ["node_modules", ".git", ".next", "out", "build"],
    },
    "natureos": {
        "path": os.getenv("NATUREOS_REPO_PATH", "/home/mycosoft/NatureOS"),
        "extensions": [".cs"],
        "exclude_dirs": [".git", "bin", "obj", "packages"],
    },
    "mindex": {
        "path": os.getenv("MINDEX_REPO_PATH", "/home/mycosoft/mindex"),
        "extensions": [".py"],
        "exclude_dirs": ["__pycache__", ".git", ".venv", "venv"],
    },
    "nlm": {
        "path": os.getenv("NLM_REPO_PATH", "/home/mycosoft/nlm"),
        "extensions": [".py"],
        "exclude_dirs": ["__pycache__", ".git", ".venv", "models", "data"],
    },
    "mycobrain": {
        "path": os.getenv("MYCOBRAIN_REPO_PATH", "/home/mycosoft/mycobrain"),
        "extensions": [".ino", ".h", ".cpp", ".hpp"],
        "exclude_dirs": [".git", "build", ".pio"],
    }
}


class CodeIndexer:
    """
    Indexes source code files across all repositories.
    """
    
    def __init__(self, registry: Optional[SystemRegistry] = None):
        self._registry = registry or get_registry()
    
    async def index_all_repositories(self) -> Dict[str, Any]:
        """Index all configured repositories."""
        results = {
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "repositories": {},
            "total_files": 0,
            "total_lines": 0,
            "errors": []
        }
        
        for repo_name, config in REPO_CONFIGS.items():
            try:
                repo_path = Path(config["path"])
                
                if not repo_path.exists():
                    logger.warning(f"Repository path not found: {repo_path}")
                    results["errors"].append({
                        "repository": repo_name,
                        "error": f"Path not found: {repo_path}"
                    })
                    continue
                
                stats = await self._index_repository(
                    repo_name, repo_path, config["extensions"], config["exclude_dirs"]
                )
                
                results["repositories"][repo_name] = stats
                results["total_files"] += stats["file_count"]
                results["total_lines"] += stats["total_lines"]
                
            except Exception as e:
                logger.error(f"Failed to index {repo_name}: {e}")
                results["errors"].append({
                    "repository": repo_name,
                    "error": str(e)
                })
        
        return results
    
    async def _index_repository(
        self,
        repo_name: str,
        repo_path: Path,
        extensions: List[str],
        exclude_dirs: List[str]
    ) -> Dict[str, Any]:
        """Index a single repository."""
        stats = {
            "file_count": 0,
            "total_lines": 0,
            "by_type": {},
            "classes": [],
            "functions": []
        }
        
        for file_path in self._find_files(repo_path, extensions, exclude_dirs):
            try:
                file_info = await self._index_file(repo_name, repo_path, file_path)
                
                if file_info:
                    await self._registry.register_code_file(file_info)
                    
                    stats["file_count"] += 1
                    stats["total_lines"] += file_info.line_count or 0
                    
                    ext = file_info.file_type
                    if ext not in stats["by_type"]:
                        stats["by_type"][ext] = {"count": 0, "lines": 0}
                    stats["by_type"][ext]["count"] += 1
                    stats["by_type"][ext]["lines"] += file_info.line_count or 0
                    
                    stats["classes"].extend(file_info.classes[:10])  # Limit
                    stats["functions"].extend(file_info.functions[:10])
                    
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
        
        logger.info(f"Indexed {stats['file_count']} files from {repo_name}")
        return stats
    
    def _find_files(
        self,
        root_path: Path,
        extensions: List[str],
        exclude_dirs: List[str]
    ) -> List[Path]:
        """Find all files with given extensions, excluding specified directories."""
        files = []
        
        for path in root_path.rglob("*"):
            # Skip excluded directories
            if any(excluded in path.parts for excluded in exclude_dirs):
                continue
            
            # Check extension
            if path.is_file() and path.suffix in extensions:
                files.append(path)
        
        return files
    
    async def _index_file(
        self,
        repo_name: str,
        repo_path: Path,
        file_path: Path
    ) -> Optional[CodeFileInfo]:
        """Index a single file."""
        try:
            relative_path = str(file_path.relative_to(repo_path))
            
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Calculate hash
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Count lines
            lines = content.split("\n")
            line_count = len(lines)
            
            # Extract code elements based on file type
            ext = file_path.suffix.lower()
            
            if ext == ".py":
                exports, imports, classes, functions = self._parse_python(content)
            elif ext in [".ts", ".tsx", ".js", ".jsx"]:
                exports, imports, classes, functions = self._parse_typescript(content)
            elif ext == ".cs":
                exports, imports, classes, functions = self._parse_csharp(content)
            elif ext in [".ino", ".cpp", ".hpp", ".h"]:
                exports, imports, classes, functions = self._parse_cpp(content)
            else:
                exports, imports, classes, functions = [], [], [], []
            
            return CodeFileInfo(
                repository=repo_name,
                file_path=relative_path,
                file_type=ext.lstrip("."),
                file_hash=file_hash,
                line_count=line_count,
                exports=exports[:50],  # Limit stored items
                imports=imports[:50],
                classes=classes[:50],
                functions=functions[:100],
                metadata={
                    "size_bytes": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    ).isoformat()
                }
            )
            
        except Exception as e:
            logger.warning(f"Error indexing {file_path}: {e}")
            return None
    
    def _parse_python(self, content: str) -> tuple:
        """Parse Python file for classes, functions, imports, exports."""
        exports = []
        imports = []
        classes = []
        functions = []
        
        # Find imports
        import_patterns = [
            r'^import\s+(\w+)',
            r'^from\s+(\S+)\s+import',
        ]
        for pattern in import_patterns:
            imports.extend(re.findall(pattern, content, re.MULTILINE))
        
        # Find classes
        class_pattern = r'^class\s+(\w+)'
        classes = re.findall(class_pattern, content, re.MULTILINE)
        
        # Find functions
        func_pattern = r'^(?:async\s+)?def\s+(\w+)\s*\('
        functions = re.findall(func_pattern, content, re.MULTILINE)
        
        # Find __all__ exports
        all_pattern = r'__all__\s*=\s*\[(.*?)\]'
        all_match = re.search(all_pattern, content, re.DOTALL)
        if all_match:
            exports = re.findall(r'"(\w+)"|\'(\w+)\'', all_match.group(1))
            exports = [e[0] or e[1] for e in exports]
        else:
            # Consider public classes and functions as exports
            exports = [c for c in classes if not c.startswith("_")]
            exports.extend([f for f in functions if not f.startswith("_")])
        
        return exports, imports, classes, functions
    
    def _parse_typescript(self, content: str) -> tuple:
        """Parse TypeScript/JavaScript file."""
        exports = []
        imports = []
        classes = []
        functions = []
        
        # Find imports
        import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
        imports = re.findall(import_pattern, content)
        
        # Find exports
        export_patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type)\s+(\w+)',
            r'export\s+\{\s*([\w\s,]+)\s*\}',
        ]
        for pattern in export_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, str):
                    exports.extend([e.strip() for e in match.split(",")])
        
        # Find classes
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find functions
        func_patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
        ]
        for pattern in func_patterns:
            functions.extend(re.findall(pattern, content))
        
        return exports, imports, classes, functions
    
    def _parse_csharp(self, content: str) -> tuple:
        """Parse C# file."""
        exports = []
        imports = []
        classes = []
        functions = []
        
        # Find usings
        imports = re.findall(r'using\s+([\w.]+);', content)
        
        # Find classes
        class_pattern = r'(?:public|private|internal|protected)?\s*(?:static\s+)?(?:partial\s+)?class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find interfaces
        interface_pattern = r'(?:public|private|internal)?\s*interface\s+(\w+)'
        classes.extend(re.findall(interface_pattern, content))
        
        # Find methods
        method_pattern = r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:override\s+)?(?:virtual\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)'
        functions = re.findall(method_pattern, content)
        
        # Public classes/interfaces are exports
        exports = [c for c in classes]
        
        return exports, imports, classes, functions
    
    def _parse_cpp(self, content: str) -> tuple:
        """Parse C++/Arduino file."""
        exports = []
        imports = []
        classes = []
        functions = []
        
        # Find includes
        imports = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
        
        # Find classes
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # Find functions
        func_pattern = r'(?:void|int|float|double|bool|char|String|uint\d+_t)\s+(\w+)\s*\([^)]*\)'
        functions = re.findall(func_pattern, content)
        
        exports = classes + functions
        
        return exports, imports, classes, functions


# Singleton
_indexer: Optional[CodeIndexer] = None


def get_code_indexer() -> CodeIndexer:
    """Get singleton indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = CodeIndexer()
    return _indexer


async def index_all_code() -> Dict[str, Any]:
    """Convenience function to index all code."""
    indexer = get_code_indexer()
    return await indexer.index_all_repositories()
