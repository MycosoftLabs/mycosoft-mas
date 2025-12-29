#!/usr/bin/env python3
"""
Document Indexing Script
Indexes all documents in Qdrant for fast vector search.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.services.document_knowledge_base import DocumentKnowledgeBase


async def main():
    """Main indexing function."""
    print("="*60)
    print("MYCOSOFT MAS - DOCUMENT INDEXING")
    print("="*60)
    print()
    
    # Initialize knowledge base
    print("Initializing knowledge base...")
    kb = DocumentKnowledgeBase()
    
    if not await kb.initialize():
        print("❌ Failed to initialize knowledge base")
        print("   Make sure Qdrant, Redis, and dependencies are available")
        sys.exit(1)
    
    print("✓ Knowledge base initialized")
    print()
    
    # Index all documents
    print("Indexing all documents...")
    stats = await kb.index_all_documents(batch_size=10)
    
    print()
    print("="*60)
    print("INDEXING COMPLETE")
    print("="*60)
    print(f"Total Documents: {stats['total']}")
    print(f"Indexed: {stats['indexed']}")
    print(f"Failed: {stats['failed']}")
    print("="*60)
    
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} documents failed to index")
        sys.exit(1)
    
    print("\n✓ All documents indexed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

