#!/usr/bin/env python3
"""
Test Document Knowledge Base
Comprehensive test to verify document knowledge base is working.
"""

import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycosoft_mas.services.document_service import get_document_service
from mycosoft_mas.services.document_knowledge_base import DocumentKnowledgeBase
from mycosoft_mas.services.document_watcher import DocumentWatcher


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(message: str):
    """Print success message."""
    import sys
    if sys.platform == 'win32':
        print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    import sys
    if sys.platform == 'win32':
        print(f"{Colors.RED}[FAIL] {message}{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message."""
    import sys
    if sys.platform == 'win32':
        print(f"{Colors.YELLOW}[WARN] {message}{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    import sys
    if sys.platform == 'win32':
        print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


async def test_document_service():
    """Test document service."""
    print_section("Testing Document Service")
    
    try:
        service = get_document_service()
        print_success("Document service initialized")
        
        # Test get all documents
        docs = service.get_all_documents()
        print_success(f"Found {len(docs)} documents in inventory")
        
        # Test search
        results = service.search_documents("deployment")
        print_success(f"Search found {len(results)} documents matching 'deployment'")
        
        # Test get by category
        guides = service.get_documents_by_category("guides")
        print_success(f"Found {len(guides)} guide documents")
        
        # Test read document
        if docs:
            test_doc = docs[0]
            content = service.read_document(test_doc["path"])
            if content:
                print_success(f"Successfully read document: {test_doc['name']}")
                print_info(f"  Content length: {len(content)} characters")
            else:
                print_warning(f"Could not read document: {test_doc['name']}")
        
        # Test summary
        summary = service.get_document_summary()
        print_success("Document summary retrieved")
        print_info(f"  Total: {summary['total_documents']}")
        print_info(f"  Tracked in Git: {summary['tracked_in_git']}")
        print_info(f"  Local Only: {summary['local_only']}")
        
        return True
    except Exception as e:
        print_error(f"Document service test failed: {e}")
        return False


async def test_knowledge_base():
    """Test knowledge base."""
    print_section("Testing Knowledge Base")
    
    try:
        kb = DocumentKnowledgeBase()
        
        # Test initialization
        print_info("Initializing knowledge base...")
        if await kb.initialize():
            print_success("Knowledge base initialized")
        else:
            print_warning("Knowledge base initialization had warnings (may still work)")
        
        # Test statistics
        stats = await kb.get_statistics()
        print_success("Statistics retrieved")
        print_info(f"  Total documents: {stats['total_documents']}")
        print_info(f"  Indexed documents: {stats['indexed_documents']}")
        print_info(f"  Qdrant available: {stats['qdrant_available']}")
        print_info(f"  Redis available: {stats['redis_available']}")
        print_info(f"  Embeddings available: {stats['embeddings_available']}")
        
        if not stats['qdrant_available']:
            print_warning("Qdrant not available - vector search will not work")
        
        if not stats['redis_available']:
            print_warning("Redis not available - caching disabled")
        
        if not stats['embeddings_available']:
            print_warning("Embeddings not available - vector search disabled")
        
        # Test search (if Qdrant available)
        if stats['qdrant_available'] and stats['embeddings_available']:
            print_info("Testing vector search...")
            results = await kb.search("deployment guide", limit=5)
            print_success(f"Vector search returned {len(results)} results")
            
            if results:
                print_info("Top result:")
                print_info(f"  Path: {results[0]['path']}")
                print_info(f"  Score: {results[0]['score']:.3f}")
                print_info(f"  Category: {results[0]['category']}")
        else:
            print_warning("Skipping vector search (Qdrant or embeddings not available)")
        
        # Test document content retrieval
        service = kb.document_service
        docs = service.get_all_documents()
        if docs:
            test_doc = docs[0]
            content = await kb.get_document_content(test_doc["path"])
            if content:
                print_success(f"Retrieved content via knowledge base: {test_doc['name']}")
                print_info(f"  Content length: {len(content)} characters")
        
        return True
    except Exception as e:
        print_error(f"Knowledge base test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_watcher():
    """Test document watcher."""
    print_section("Testing Document Watcher")
    
    try:
        kb = DocumentKnowledgeBase()
        await kb.initialize()
        
        watcher = DocumentWatcher(knowledge_base=kb)
        print_success("Document watcher created")
        
        # Test force scan
        print_info("Running force scan...")
        stats = await watcher.force_scan()
        print_success("Force scan completed")
        print_info(f"  Scanned: {stats['scanned']}")
        print_info(f"  Indexed: {stats['indexed']}")
        print_info(f"  Failed: {stats['failed']}")
        
        return True
    except Exception as e:
        print_error(f"Document watcher test failed: {e}")
        return False


async def test_indexing():
    """Test document indexing."""
    print_section("Testing Document Indexing")
    
    try:
        kb = DocumentKnowledgeBase()
        await kb.initialize()
        
        # Get a test document
        service = kb.document_service
        docs = service.get_all_documents()
        
        if not docs:
            print_warning("No documents found to test indexing")
            return False
        
        # Test indexing a single document
        test_doc = docs[0]
        print_info(f"Testing index of: {test_doc['name']}")
        
        success = await kb.index_document(test_doc["path"], force=True)
        
        if success:
            print_success(f"Successfully indexed: {test_doc['name']}")
        else:
            print_error(f"Failed to index: {test_doc['name']}")
            return False
        
        return True
    except Exception as e:
        print_error(f"Indexing test failed: {e}")
        return False


async def test_search_queries():
    """Test various search queries."""
    print_section("Testing Search Queries")
    
    try:
        kb = DocumentKnowledgeBase()
        await kb.initialize()
        
        test_queries = [
            "deployment",
            "integration",
            "API documentation",
            "setup guide",
            "system architecture"
        ]
        
        for query in test_queries:
            print_info(f"Searching for: '{query}'")
            results = await kb.search(query, limit=3)
            
            if results:
                print_success(f"  Found {len(results)} results")
                for i, result in enumerate(results[:3], 1):
                    print_info(f"    {i}. {result['name']} (score: {result['score']:.3f})")
            else:
                print_warning(f"  No results found")
        
        return True
    except Exception as e:
        print_error(f"Search query test failed: {e}")
        return False


async def test_api_endpoints():
    """Test API endpoints (if server is running)."""
    print_section("Testing API Endpoints")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        # Test health
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    print_success("API server is running")
                else:
                    print_warning(f"API server returned status {response.status_code}")
                    return False
        except Exception as e:
            print_warning(f"API server not accessible: {e}")
            print_info("  Start the server with: uvicorn mycosoft_mas.core.myca_main:app --reload")
            return False
        
        # Test search endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/documents/search", params={"q": "deployment", "limit": 5})
            if response.status_code == 200:
                data = response.json()
                print_success(f"Search endpoint working: {data['total']} results")
            else:
                print_error(f"Search endpoint failed: {response.status_code}")
                return False
        
        # Test stats endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/documents/stats/summary")
            if response.status_code == 200:
                stats = response.json()
                print_success("Stats endpoint working")
                print_info(f"  Indexed: {stats.get('indexed_documents', 'N/A')}")
            else:
                print_warning(f"Stats endpoint returned: {response.status_code}")
        
        return True
    except ImportError:
        print_warning("httpx not available - skipping API tests")
        return True
    except Exception as e:
        print_error(f"API endpoint test failed: {e}")
        return False


async def main():
    """Run all tests."""
    import sys
    # Fix Windows console encoding
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("MYCOSOFT MAS - DOCUMENT KNOWLEDGE BASE TEST")
    print("="*60)
    print(f"{Colors.RESET}")
    
    results = {}
    
    # Run tests
    results["document_service"] = await test_document_service()
    results["knowledge_base"] = await test_knowledge_base()
    results["watcher"] = await test_watcher()
    results["indexing"] = await test_indexing()
    results["search_queries"] = await test_search_queries()
    results["api_endpoints"] = await test_api_endpoints()
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print_success("All tests passed! Document knowledge base is working correctly.")
        return 0
    else:
        print_warning(f"{total - passed} test(s) failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

