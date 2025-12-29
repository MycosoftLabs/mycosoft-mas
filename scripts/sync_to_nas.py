#!/usr/bin/env python3
"""
NAS Document Sync
Syncs all documents to the NAS shared drive (M-Y-C-A-L).
Supports both Windows (SMB) and Linux (NFS/SMB) mounting.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import platform

class NASSync:
    def __init__(self, nas_path: str, inventory_path: str = "docs/document_inventory.json"):
        """
        Initialize NAS sync.
        
        Args:
            nas_path: Path to NAS mount point (e.g., "\\\\M-Y-C-A-L\\docs" or "/mnt/mycosoft-nas/docs")
            inventory_path: Path to document inventory JSON
        """
        self.nas_path = Path(nas_path)
        self.inventory_path = Path(inventory_path)
        self.docs_base = "mycosoft-mas-docs"
        
    def ensure_nas_path(self):
        """Ensure NAS path exists and is accessible."""
        if not self.nas_path.exists():
            try:
                self.nas_path.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created NAS directory: {self.nas_path}")
            except Exception as e:
                print(f"❌ Cannot create NAS directory: {e}")
                raise
        
        # Test write access
        test_file = self.nas_path / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print(f"✓ NAS path is writable: {self.nas_path}")
        except Exception as e:
            print(f"❌ NAS path is not writable: {e}")
            raise
    
    def get_target_path(self, doc_path: str) -> Path:
        """Get target path on NAS for a document."""
        # Preserve directory structure
        return self.nas_path / self.docs_base / doc_path
    
    def sync_document(self, doc_info: Dict, root_path: Path) -> bool:
        """Sync a single document to NAS."""
        source_path = root_path / doc_info["path"]
        target_path = self.get_target_path(doc_info["path"])
        
        if not source_path.exists():
            print(f"⚠️  Source file not found: {source_path}")
            return False
        
        try:
            # Create target directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Verify
            if target_path.exists() and target_path.stat().st_size == source_path.stat().st_size:
                return True
            else:
                print(f"⚠️  Verification failed for {doc_info['name']}")
                return False
        except Exception as e:
            print(f"❌ Error syncing {doc_info['name']}: {e}")
            return False
    
    def create_index(self, documents: List[Dict], root_path: Path):
        """Create index files on NAS."""
        # Create JSON index
        index_path = self.nas_path / self.docs_base / "index.json"
        index_data = {
            "sync_timestamp": datetime.now().isoformat(),
            "total_documents": len(documents),
            "documents": documents,
            "nas_path": str(self.nas_path),
            "base_path": str(self.nas_path / self.docs_base)
        }
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created index: {index_path}")
        
        # Create markdown index
        md_index_path = self.nas_path / self.docs_base / "INDEX.md"
        lines = [
            "# Mycosoft MAS - NAS Document Index",
            "",
            f"*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            f"**Total Documents**: {len(documents)}",
            "",
            "## Documents",
            ""
        ]
        
        for doc in sorted(documents, key=lambda x: x["path"]):
            lines.append(f"- [{doc['name']}]({doc['path']})")
            lines.append(f"  - Path: `{doc['path']}`")
            lines.append(f"  - Category: {doc['category']}")
            lines.append(f"  - Size: {doc['size_bytes']:,} bytes")
            lines.append("")
        
        with open(md_index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Created markdown index: {md_index_path}")
    
    def sync_all(self):
        """Sync all documents from inventory to NAS."""
        if not self.inventory_path.exists():
            print(f"❌ Inventory file not found: {self.inventory_path}")
            return
        
        # Load inventory
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        root_path = Path(data["metadata"]["root_path"])
        documents = data["documents"]
        
        # Ensure NAS path
        self.ensure_nas_path()
        
        print(f"📤 Syncing {len(documents)} documents to NAS...")
        print(f"   Source: {root_path}")
        print(f"   Target: {self.nas_path / self.docs_base}")
        
        synced = 0
        failed = 0
        
        for doc in documents:
            if self.sync_document(doc, root_path):
                synced += 1
                if synced % 10 == 0:
                    print(f"   Progress: {synced}/{len(documents)}")
            else:
                failed += 1
        
        # Create index files
        self.create_index(documents, root_path)
        
        print(f"\n✓ Synced: {synced}")
        if failed > 0:
            print(f"⚠️  Failed: {failed}")
        
        print(f"\n📁 Documents available at: {self.nas_path / self.docs_base}")


def get_nas_path() -> Optional[str]:
    """Get NAS path from environment or detect common locations."""
    # Check environment variable
    nas_path = os.getenv("NAS_DOCS_PATH")
    if nas_path:
        return nas_path
    
    # Try common Windows paths
    if platform.system() == "Windows":
        common_paths = [
            r"\\M-Y-C-A-L\docs",
            r"\\M-Y-C-A-L\shared\docs",
            r"\\192.168.1.100\docs",
            r"Z:\docs",
            r"Y:\docs"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    # Try common Linux paths
    else:
        common_paths = [
            "/mnt/mycosoft-nas/docs",
            "/mnt/nas/docs",
            "/media/nas/docs"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    return None


def main():
    """Main entry point."""
    nas_path = get_nas_path()
    
    if not nas_path:
        print("❌ NAS path not found. Please set NAS_DOCS_PATH environment variable")
        print("   Example (Windows): set NAS_DOCS_PATH=\\\\M-Y-C-A-L\\docs")
        print("   Example (Linux): export NAS_DOCS_PATH=/mnt/mycosoft-nas/docs")
        return
    
    print(f"📁 Using NAS path: {nas_path}")
    
    sync = NASSync(nas_path)
    sync.sync_all()


if __name__ == "__main__":
    main()

