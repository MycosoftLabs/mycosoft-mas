"""
Simple webhook proxy to bridge n8n-style webhooks to MAS Orchestrator
This provides instant functionality while n8n workflows are being set up
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="MYCA Webhook Proxy")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAS_URL = "http://localhost:8001"

@app.get("/health")
async def health():
    return {"status": "ok", "service": "webhook-proxy"}

@app.post("/webhook/{path:path}")
async def webhook_proxy(path: str, request: Request):
    """Proxy webhook requests to appropriate MAS endpoints"""
    
    try:
        body = await request.json()
    except:
        body = {}
    
    logger.info(f"Webhook: /{path} - Body: {body}")
    
    # Route based on path
    if "brain" in path or "jarvis" in path or "chat" in path:
        # Route to voice orchestrator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MAS_URL}/voice/orchestrator/chat",
                json={"message": body.get("message", "Hello"), "conversation_id": body.get("conversation_id", "proxy")},
                timeout=30.0
            )
            return response.json()
    
    elif "system" in path:
        # System status
        async with httpx.AsyncClient() as client:
            health = await client.get(f"{MAS_URL}/health", timeout=10.0)
            registry = await client.get(f"{MAS_URL}/agents/registry/", timeout=10.0)
            return {
                "system": health.json(),
                "agents": registry.json(),
                "message": "System operational"
            }
    
    elif "tools" in path:
        # Generic tool response
        return {
            "status": "ok",
            "message": f"Tools endpoint received: {body}",
            "action": body.get("action", "unknown")
        }
    
    elif "business" in path:
        # Business operations
        return {
            "status": "ok",
            "message": f"Business operations endpoint received: {body}",
            "domain": body.get("domain", "unknown")
        }
    
    else:
        # Echo back
        return {
            "status": "ok",
            "webhook_path": path,
            "received": body,
            "message": "Webhook proxy received your request"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5679)
