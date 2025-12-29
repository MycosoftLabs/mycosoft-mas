"""
Document Watcher Service
Automatically detects and indexes new markdown/README files.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime
import hashlib
import time

from mycosoft_mas.services.document_service import get_document_service
from mycosoft_mas.services.document_knowledge_base import DocumentKnowledgeBase

logger = logging.getLogger(__name__)


class DocumentWatcher:
    """Watches for new or modified markdown/README files and auto-indexes them."""
    
    def __init__(
        self,
        root_path: str = ".",
        watch_interval: int = 60,
        knowledge_base: Optional[DocumentKnowledgeBase] = None
    ):
        """
        Initialize document watcher.
        
        Args:
            root_path: Root directory to watch
            watch_interval: Seconds between scans
            knowledge_base: Knowledge base instance (optional)
        """
        self.root_path = Path(root_path).resolve()
        self.watch_interval = watch_interval
        self.knowledge_base = knowledge_base
        
        self.document_service = get_document_service()
        self.is_running = False
        self._watched_files: Set[str] = set()
        self._file_hashes: Dict[str, str] = {}
        
        logger.info(f"DocumentWatcher initialized for {self.root_path}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _is_document_file(self, file_path: Path) -> bool:
        """Check if file is a document we should index."""
        name = file_path.name.lower()
        
        # Check extensions
        if file_path.suffix.lower() == '.md':
            return True
        
        # Check README patterns
        if name.startswith('readme') or name == 'readme':
            return True
        
        return False
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        # Ignore hidden directories and common exclusions
        parts = file_path.parts
        for part in parts:
            if part.startswith('.') and part not in ['.', '..']:
                return True
            if part in ['node_modules', 'venv', '__pycache__', '.git', 'dist', 'build']:
                return True
        
        return False
    
    async def scan_for_new_documents(self) -> Set[str]:
        """Scan for new or modified documents."""
        new_documents: Set[str] = []
        
        try:
            # Get all markdown/README files
            patterns = ["*.md", "README*", "*.MD"]
            current_files: Set[str] = set()
            
            for pattern in patterns:
                for file_path in self.root_path.rglob(pattern):
                    if file_path.is_file() and not self._should_ignore(file_path):
                        rel_path = str(file_path.relative_to(self.root_path)).replace("\\", "/")
                        current_files.add(rel_path)
                        
                        # Check if new or modified
                        current_hash = self._get_file_hash(file_path)
                        previous_hash = self._file_hashes.get(rel_path)
                        
                        if rel_path not in self._watched_files or current_hash != previous_hash:
                            new_documents.append(rel_path)
                            self._file_hashes[rel_path] = current_hash
            
            # Update watched files
            self._watched_files = current_files
            
        except Exception as e:
            logger.error(f"Error scanning for documents: {e}")
        
        return set(new_documents)
    
    async def index_document(self, doc_path: str) -> bool:
        """Index a document in the knowledge base."""
        if not self.knowledge_base:
            logger.warning("Knowledge base not available, skipping index")
            return False
        
        try:
            success = await self.knowledge_base.index_document(doc_path, force=True)
            if success:
                logger.info(f"Auto-indexed document: {doc_path}")
            else:
                logger.warning(f"Failed to index document: {doc_path}")
            return success
        except Exception as e:
            logger.error(f"Error indexing document {doc_path}: {e}")
            return False
    
    async def watch_loop(self):
        """Main watch loop."""
        logger.info("Document watcher started")
        
        # Initial scan
        logger.info("Performing initial scan...")
        initial_docs = await self.scan_for_new_documents()
        if initial_docs:
            logger.info(f"Found {len(initial_docs)} documents in initial scan")
            for doc_path in initial_docs:
                await self.index_document(doc_path)
        
        # Watch loop
        while self.is_running:
            try:
                await asyncio.sleep(self.watch_interval)
                
                # Scan for new/modified documents
                new_docs = await self.scan_for_new_documents()
                
                if new_docs:
                    logger.info(f"Found {len(new_docs)} new/modified documents")
                    for doc_path in new_docs:
                        await self.index_document(doc_path)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def start(self):
        """Start the watcher."""
        if self.is_running:
            logger.warning("Watcher already running")
            return
        
        self.is_running = True
        
        # Initialize knowledge base if not provided
        if not self.knowledge_base:
            try:
                self.knowledge_base = DocumentKnowledgeBase()
                await self.knowledge_base.initialize()
                logger.info("Knowledge base initialized for watcher")
            except Exception as e:
                logger.warning(f"Could not initialize knowledge base: {e}")
        
        # Start watch loop in background
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.watch_loop())
        except RuntimeError:
            # No event loop, create new one
            asyncio.create_task(self.watch_loop())
        
        logger.info("Document watcher started")
    
    async def stop(self):
        """Stop the watcher."""
        self.is_running = False
        logger.info("Document watcher stopped")
    
    async def force_scan(self) -> Dict[str, int]:
        """Force a scan and return statistics."""
        new_docs = await self.scan_for_new_documents()
        
        indexed = 0
        failed = 0
        
        for doc_path in new_docs:
            if await self.index_document(doc_path):
                indexed += 1
            else:
                failed += 1
        
        return {
            "scanned": len(new_docs),
            "indexed": indexed,
            "failed": failed
        }


# Global instance
_watcher: Optional[DocumentWatcher] = None

async def get_document_watcher(
    knowledge_base: Optional[DocumentKnowledgeBase] = None
) -> DocumentWatcher:
    """Get global document watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = DocumentWatcher(knowledge_base=knowledge_base)
    return _watcher

