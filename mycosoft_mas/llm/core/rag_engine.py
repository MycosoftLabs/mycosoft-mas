"""
RAG Engine - Retrieval Augmented Generation
For MYCA scientific knowledge retrieval and generation.
Created: February 3, 2026
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel
from .model_wrapper import LLMWrapper, Message, get_llm_wrapper

logger = logging.getLogger(__name__)

class Document(BaseModel):
    doc_id: UUID
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    score: float = 0.0

class RetrievalResult(BaseModel):
    query: str
    documents: List[Document]
    total_found: int

class RAGEngine:
    """Retrieval Augmented Generation engine for scientific knowledge."""
    
    def __init__(self, llm: Optional[LLMWrapper] = None, vector_store: Optional[Any] = None):
        self.llm = llm or get_llm_wrapper("openai", "gpt-4-turbo")
        self.vector_store = vector_store
        self._document_cache: Dict[UUID, Document] = {}
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.top_k = 5
        logger.info("RAG Engine initialized")
    
    async def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> UUID:
        doc_id = uuid4()
        embedding = await self.llm.embed(content[:8000])
        doc = Document(doc_id=doc_id, content=content, metadata=metadata or {}, embedding=embedding)
        self._document_cache[doc_id] = doc
        logger.info(f"Added document: {doc_id}")
        return doc_id
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> List[UUID]:
        doc_ids = []
        for doc in documents:
            doc_id = await self.add_document(doc.get("content", ""), doc.get("metadata"))
            doc_ids.append(doc_id)
        return doc_ids
    
    async def retrieve(self, query: str, top_k: Optional[int] = None) -> RetrievalResult:
        k = top_k or self.top_k
        query_embedding = await self.llm.embed(query)
        scored_docs = []
        for doc in self._document_cache.values():
            if doc.embedding:
                score = self._cosine_similarity(query_embedding, doc.embedding)
                doc.score = score
                scored_docs.append(doc)
        scored_docs.sort(key=lambda x: x.score, reverse=True)
        top_docs = scored_docs[:k]
        return RetrievalResult(query=query, documents=top_docs, total_found=len(scored_docs))
    
    async def generate(self, query: str, context_docs: Optional[List[Document]] = None, system_prompt: Optional[str] = None) -> str:
        if context_docs is None:
            result = await self.retrieve(query)
            context_docs = result.documents
        context = "\n\n---\n\n".join([f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.content}" for d in context_docs])
        prompt = f"""Use the following context to answer the question. If the context does not contain enough information, say so.

Context:
{context}

Question: {query}

Answer:"""
        messages = [
            Message(role="system", content=system_prompt or "You are a helpful scientific assistant."),
            Message(role="user", content=prompt)
        ]
        response = await self.llm.generate(messages)
        return response.content
    
    async def query(self, query: str) -> Dict[str, Any]:
        result = await self.retrieve(query)
        answer = await self.generate(query, result.documents)
        return {
            "query": query,
            "answer": answer,
            "sources": [{"doc_id": str(d.doc_id), "score": d.score, "metadata": d.metadata} for d in result.documents]
        }
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b): return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot_product / (norm_a * norm_b)
    
    def chunk_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks
    
    async def index_knowledge_base(self, documents: List[Dict[str, Any]]) -> int:
        count = 0
        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            if len(content) > self.chunk_size:
                chunks = self.chunk_text(content)
                for i, chunk in enumerate(chunks):
                    chunk_meta = {**metadata, "chunk_index": i}
                    await self.add_document(chunk, chunk_meta)
                    count += 1
            else:
                await self.add_document(content, metadata)
                count += 1
        logger.info(f"Indexed {count} chunks from {len(documents)} documents")
        return count
