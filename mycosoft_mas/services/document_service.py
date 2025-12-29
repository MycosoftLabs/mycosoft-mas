"""
Document Service for MYCA Agents
Provides instant access to all system documents for agents and tools.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import os

class DocumentService:
    """Service for accessing system documents."""
    
    def __init__(self, inventory_path: Optional[str] = None, nas_path: Optional[str] = None):
        """
        Initialize document service.
        
        Args:
            inventory_path: Path to document inventory JSON (default: docs/document_inventory.json)
            nas_path: Path to NAS documents (optional, for faster access)
        """
        self.root_path = Path(__file__).parent.parent.parent
        self.inventory_path = Path(inventory_path) if inventory_path else self.root_path / "docs" / "document_inventory.json"
        self.nas_path = Path(nas_path) if nas_path else None
        
        self._inventory: Optional[Dict] = None
        self._documents_cache: Dict[str, Dict] = {}
    
    def load_inventory(self) -> Dict:
        """Load document inventory."""
        if self._inventory is not None:
            return self._inventory
        
        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory not found: {self.inventory_path}")
        
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            self._inventory = json.load(f)
        
        return self._inventory
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents from inventory."""
        inventory = self.load_inventory()
        return inventory.get("documents", [])
    
    def get_document_by_path(self, path: str) -> Optional[Dict]:
        """Get document info by path."""
        documents = self.get_all_documents()
        for doc in documents:
            if doc["path"] == path or doc["id"] == path:
                return doc
        return None
    
    def get_documents_by_category(self, category: str) -> List[Dict]:
        """Get all documents in a category."""
        documents = self.get_all_documents()
        return [d for d in documents if d["category"] == category]
    
    def search_documents(self, query: str) -> List[Dict]:
        """Search documents by name or path."""
        query_lower = query.lower()
        documents = self.get_all_documents()
        results = []
        
        for doc in documents:
            if (query_lower in doc["name"].lower() or 
                query_lower in doc["path"].lower() or
                query_lower in doc.get("category", "").lower()):
                results.append(doc)
        
        return results
    
    def read_document(self, doc_path: str, use_nas: bool = True) -> Optional[str]:
        """
        Read document content.
        
        Args:
            doc_path: Document path (relative or absolute)
            use_nas: Try NAS path first if available
        
        Returns:
            Document content or None if not found
        """
        # Try NAS first if available
        if use_nas and self.nas_path:
            nas_doc_path = self.nas_path / "mycosoft-mas-docs" / doc_path
            if nas_doc_path.exists():
                try:
                    return nas_doc_path.read_text(encoding='utf-8')
                except Exception:
                    pass
        
        # Fall back to local path
        doc_info = self.get_document_by_path(doc_path)
        if doc_info:
            local_path = Path(doc_info["absolute_path"])
            if local_path.exists():
                try:
                    return local_path.read_text(encoding='utf-8')
                except Exception:
                    pass
        
        # Try direct path
        local_path = self.root_path / doc_path
        if local_path.exists():
            try:
                return local_path.read_text(encoding='utf-8')
            except Exception:
                pass
        
        return None
    
    def get_document_summary(self) -> Dict:
        """Get summary statistics."""
        inventory = self.load_inventory()
        metadata = inventory.get("metadata", {})
        summary = metadata.get("summary", {})
        
        return {
            "total_documents": summary.get("total_documents", 0),
            "tracked_in_git": summary.get("tracked_in_git", 0),
            "local_only": summary.get("local_only", 0),
            "total_size_mb": summary.get("total_size_mb", 0),
            "categories": summary.get("category_breakdown", {}),
            "last_updated": metadata.get("generated", "")
        }
    
    def get_related_documents(self, doc_path: str, max_results: int = 5) -> List[Dict]:
        """Get related documents (same directory or category)."""
        doc = self.get_document_by_path(doc_path)
        if not doc:
            return []
        
        documents = self.get_all_documents()
        related = []
        
        doc_dir = Path(doc["path"]).parent
        doc_category = doc["category"]
        
        for other_doc in documents:
            if other_doc["path"] == doc_path:
                continue
            
            other_dir = Path(other_doc["path"]).parent
            other_category = other_doc["category"]
            
            score = 0
            if other_dir == doc_dir:
                score += 2
            if other_category == doc_category:
                score += 1
            
            if score > 0:
                related.append((score, other_doc))
        
        # Sort by score and return top results
        related.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in related[:max_results]]
    
    def get_document_tree(self) -> Dict:
        """Get hierarchical document tree structure."""
        documents = self.get_all_documents()
        tree = {}
        
        for doc in documents:
            parts = Path(doc["path"]).parts
            current = tree
            
            for part in parts[:-1]:  # All but filename
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file
            filename = parts[-1]
            current[filename] = doc
        
        return tree


# Global instance for easy access
_document_service: Optional[DocumentService] = None

def get_document_service() -> DocumentService:
    """Get global document service instance."""
    global _document_service
    if _document_service is None:
        nas_path = os.getenv("NAS_DOCS_PATH")
        _document_service = DocumentService(nas_path=nas_path)
    return _document_service

