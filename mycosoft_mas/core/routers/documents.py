"""
Document API Router
Fast search and access endpoints for documents.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel

from mycosoft_mas.services.document_knowledge_base import get_knowledge_base, DocumentKnowledgeBase

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentSearchRequest(BaseModel):
    query: str
    limit: int = 10
    category: Optional[str] = None
    min_score: float = 0.5


class DocumentSearchResponse(BaseModel):
    results: List[dict]
    total: int
    query: str


class DocumentContentResponse(BaseModel):
    path: str
    name: str
    content: str
    metadata: dict


@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_score: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity score"),
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> DocumentSearchResponse:
    """
    Search documents using vector similarity.
    
    Example:
        GET /documents/search?q=deployment&limit=5&category=deployment
    """
    try:
        results = await kb.search(
            query=q,
            limit=limit,
            category=category,
            min_score=min_score
        )
        
        return DocumentSearchResponse(
            results=results,
            total=len(results),
            query=q
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search")
async def search_documents_post(
    request: DocumentSearchRequest,
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> DocumentSearchResponse:
    """
    Search documents using vector similarity (POST version).
    
    Example:
        POST /documents/search
        {
            "query": "deployment guide",
            "limit": 10,
            "category": "deployment",
            "min_score": 0.6
        }
    """
    try:
        results = await kb.search(
            query=request.query,
            limit=request.limit,
            category=request.category,
            min_score=request.min_score
        )
        
        return DocumentSearchResponse(
            results=results,
            total=len(results),
            query=request.query
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{doc_path:path}")
async def get_document(
    doc_path: str,
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> DocumentContentResponse:
    """
    Get full document content.
    
    Example:
        GET /documents/docs/SYSTEM_INTEGRATIONS.md
    """
    try:
        # Get document info
        doc_service = kb.document_service
        doc_info = doc_service.get_document_by_path(doc_path)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")
        
        # Get content
        content = await kb.get_document_content(doc_path)
        
        if not content:
            raise HTTPException(status_code=404, detail=f"Could not read document: {doc_path}")
        
        return DocumentContentResponse(
            path=doc_path,
            name=doc_info["name"],
            content=content,
            metadata={
                "category": doc_info["category"],
                "size": doc_info["size_bytes"],
                "modified": doc_info["modified"],
                "hash": doc_info["hash"],
                "url_github": doc_info.get("url_github")
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading document: {str(e)}")


@router.get("/{doc_path:path}/related")
async def get_related_documents(
    doc_path: str,
    limit: int = Query(5, ge=1, le=20),
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> DocumentSearchResponse:
    """
    Get documents related to the specified document.
    
    Example:
        GET /documents/docs/SYSTEM_INTEGRATIONS.md/related?limit=5
    """
    try:
        results = await kb.get_related_documents(doc_path, limit=limit)
        
        return DocumentSearchResponse(
            results=results,
            total=len(results),
            query=f"related to {doc_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding related documents: {str(e)}")


@router.get("/stats/summary")
async def get_statistics(
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> dict:
    """
    Get knowledge base statistics.
    
    Example:
        GET /documents/stats/summary
    """
    try:
        stats = await kb.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.post("/index/{doc_path:path}")
async def index_document(
    doc_path: str,
    force: bool = Query(False, description="Force re-indexing"),
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> dict:
    """
    Index a document in the knowledge base.
    
    Example:
        POST /documents/index/docs/SYSTEM_INTEGRATIONS.md?force=true
    """
    try:
        success = await kb.index_document(doc_path, force=force)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to index document: {doc_path}")
        
        return {
            "status": "success",
            "path": doc_path,
            "indexed": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")


@router.post("/watch/start")
async def start_watcher(
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> dict:
    """
    Start the document watcher for automatic indexing.
    
    Example:
        POST /documents/watch/start
    """
    try:
        from mycosoft_mas.services.document_watcher import get_document_watcher
        
        watcher = await get_document_watcher(knowledge_base=kb)
        await watcher.start()
        
        return {
            "status": "success",
            "message": "Document watcher started",
            "watch_interval": watcher.watch_interval
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting watcher: {str(e)}")


@router.post("/watch/scan")
async def force_scan(
    kb: DocumentKnowledgeBase = Depends(get_knowledge_base)
) -> dict:
    """
    Force a scan for new/modified documents.
    
    Example:
        POST /documents/watch/scan
    """
    try:
        from mycosoft_mas.services.document_watcher import get_document_watcher
        
        watcher = await get_document_watcher(knowledge_base=kb)
        stats = await watcher.force_scan()
        
        return {
            "status": "success",
            "scanned": stats["scanned"],
            "indexed": stats["indexed"],
            "failed": stats["failed"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning: {str(e)}")

