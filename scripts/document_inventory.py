#!/usr/bin/env python3
"""
Document Inventory Scanner
Scans the entire codebase for markdown and README files,
creates a comprehensive inventory with metadata.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import subprocess

class DocumentInventory:
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.inventory: List[Dict] = []
        self.categories = {
            "root": [],
            "docs": [],
            "readme": [],
            "guides": [],
            "reports": [],
            "integration": [],
            "deployment": [],
            "agent": [],
            "module": [],
            "service": [],
            "other": []
        }
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def get_git_status(self, file_path: Path) -> Dict[str, any]:
        """Check if file is tracked in git and get status."""
        try:
            rel_path = file_path.relative_to(self.root_path)
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(rel_path)],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            is_tracked = result.returncode == 0
            
            # Check if modified
            is_modified = False
            if is_tracked:
                result = subprocess.run(
                    ["git", "diff", "--quiet", str(rel_path)],
                    cwd=self.root_path,
                    capture_output=True,
                    timeout=5
                )
                is_modified = result.returncode != 0
            
            return {
                "tracked": is_tracked,
                "modified": is_modified,
                "on_github": is_tracked  # Assuming tracked = on GitHub
            }
        except Exception:
            return {"tracked": False, "modified": False, "on_github": False}
    
    def categorize_document(self, file_path: Path) -> str:
        """Categorize document based on path and name."""
        rel_path = str(file_path.relative_to(self.root_path)).lower()
        name = file_path.name.lower()
        
        if name == "readme.md":
            return "readme"
        elif "readme" in name:
            return "readme"
        elif "docs/" in rel_path:
            if "/agents/" in rel_path:
                return "agent"
            elif "/modules/" in rel_path:
                return "module"
            elif "/services/" in rel_path:
                return "service"
            elif "/integrations/" in rel_path:
                return "integration"
            else:
                return "docs"
        elif any(x in name for x in ["guide", "setup", "install", "quickstart"]):
            return "guides"
        elif any(x in name for x in ["report", "summary", "status", "changelog"]):
            return "reports"
        elif any(x in name for x in ["deployment", "docker", "azure", "production"]):
            return "deployment"
        elif "integration" in rel_path or "integration" in name:
            return "integration"
        elif file_path.parent == self.root_path:
            return "root"
        else:
            return "other"
    
    def scan_documents(self) -> List[Dict]:
        """Scan all markdown and README files in the repository."""
        patterns = ["*.md", "README*", "*.MD"]
        documents = []
        
        for pattern in patterns:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file() and not any(
                    part.startswith('.') or part in ['node_modules', 'venv', '__pycache__', '.git']
                    for part in file_path.parts
                ):
                    rel_path = file_path.relative_to(self.root_path)
                    stat = file_path.stat()
                    
                    git_status = self.get_git_status(file_path)
                    category = self.categorize_document(file_path)
                    
                    doc_info = {
                        "id": str(rel_path).replace("\\", "/"),
                        "name": file_path.name,
                        "path": str(rel_path).replace("\\", "/"),
                        "absolute_path": str(file_path),
                        "category": category,
                        "directory": str(rel_path.parent).replace("\\", "/"),
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "hash": self.get_file_hash(file_path),
                        "git": git_status,
                        "url_local": f"file:///{file_path.as_uri().replace('file:///', '')}",
                        "url_github": f"https://github.com/mycosoft/mycosoft-mas/blob/main/{rel_path.as_posix()}" if git_status["tracked"] else None,
                        "notion_ready": True,
                        "nas_synced": False
                    }
                    
                    documents.append(doc_info)
                    self.categories[category].append(doc_info)
        
        # Sort by path
        documents.sort(key=lambda x: x["path"])
        self.inventory = documents
        return documents
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        total = len(self.inventory)
        tracked = sum(1 for d in self.inventory if d["git"]["tracked"])
        modified = sum(1 for d in self.inventory if d["git"]["modified"])
        local_only = sum(1 for d in self.inventory if not d["git"]["tracked"])
        
        category_counts = {cat: len(docs) for cat, docs in self.categories.items()}
        
        total_size = sum(d["size_bytes"] for d in self.inventory)
        
        return {
            "total_documents": total,
            "tracked_in_git": tracked,
            "modified": modified,
            "local_only": local_only,
            "on_github": tracked - modified,
            "category_breakdown": category_counts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "scan_timestamp": datetime.now().isoformat()
        }
    
    def save_inventory(self, output_path: str = "docs/document_inventory.json"):
        """Save inventory to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        inventory_data = {
            "metadata": {
                "version": "1.0",
                "generated": datetime.now().isoformat(),
                "root_path": str(self.root_path),
                "summary": self.generate_summary()
            },
            "documents": self.inventory,
            "categories": {
                cat: [d["id"] for d in docs]
                for cat, docs in self.categories.items()
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(inventory_data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Inventory saved to {output_file}")
        return output_file
    
    def generate_markdown_index(self, output_path: str = "DOCUMENT_INDEX.md"):
        """Generate a markdown index of all documents."""
        output_file = Path(output_path)
        
        lines = [
            "# Mycosoft MAS - Complete Document Index",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Summary",
            "",
            f"- **Total Documents**: {len(self.inventory)}",
            f"- **Tracked in Git**: {sum(1 for d in self.inventory if d['git']['tracked'])}",
            f"- **Local Only**: {sum(1 for d in self.inventory if not d['git']['tracked'])}",
            "",
            "## Documents by Category",
            ""
        ]
        
        # Add category sections
        for category, docs in sorted(self.categories.items()):
            if not docs:
                continue
            
            lines.append(f"### {category.replace('_', ' ').title()} ({len(docs)})")
            lines.append("")
            
            for doc in sorted(docs, key=lambda x: x["path"]):
                status = ""
                if not doc["git"]["tracked"]:
                    status = " 🏠 *Local Only*"
                elif doc["git"]["modified"]:
                    status = " ✏️ *Modified*"
                
                github_link = f" | [GitHub]({doc['url_github']})" if doc["url_github"] else ""
                
                lines.append(
                    f"- [{doc['name']}]({doc['path']}){status}{github_link}"
                )
                lines.append(f"  - Path: `{doc['path']}`")
                lines.append(f"  - Category: {doc['category']}")
                lines.append(f"  - Size: {doc['size_bytes']:,} bytes")
                lines.append("")
        
        # Add all documents list
        lines.extend([
            "## All Documents (Alphabetical)",
            ""
        ])
        
        for doc in sorted(self.inventory, key=lambda x: x["path"]):
            status_icons = []
            if not doc["git"]["tracked"]:
                status_icons.append("🏠 Local")
            if doc["git"]["modified"]:
                status_icons.append("✏️ Modified")
            if doc["git"]["on_github"]:
                status_icons.append("📦 GitHub")
            
            status_str = f" *({', '.join(status_icons)})*" if status_icons else ""
            
            lines.append(f"- [{doc['path']}]({doc['path']}){status_str}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"[OK] Markdown index saved to {output_file}")
        return output_file


def main():
    """Main entry point."""
    import sys
    # Fix Windows console encoding
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("Scanning documents...")
    
    inventory = DocumentInventory()
    documents = inventory.scan_documents()
    
    print(f"Found {len(documents)} documents")
    
    # Save inventory
    inventory.save_inventory()
    
    # Generate markdown index
    inventory.generate_markdown_index()
    
    # Print summary
    summary = inventory.generate_summary()
    print("\n" + "="*60)
    print("DOCUMENT INVENTORY SUMMARY")
    print("="*60)
    print(f"Total Documents: {summary['total_documents']}")
    print(f"Tracked in Git: {summary['tracked_in_git']}")
    print(f"Local Only: {summary['local_only']}")
    print(f"Modified: {summary['modified']}")
    print(f"Total Size: {summary['total_size_mb']} MB")
    print("\nBy Category:")
    for cat, count in summary['category_breakdown'].items():
        if count > 0:
            print(f"  {cat}: {count}")
    print("="*60)


if __name__ == "__main__":
    main()

