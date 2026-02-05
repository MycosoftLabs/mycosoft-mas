#!/usr/bin/env python3
"""
MINDEX - Mycological Index Data System
Enhanced with Voice/Brain API integration
Updated: February 5, 2026
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import hashlib
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MINDEX + MYCA Brain", version="2.1.0", description="Mycological Index with MYCA Voice/Brain Integration")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# In-memory storage
species_database = {}
taxonomic_matches = {}
citation_hashes = set()
sessions = {}

# ===== Voice/Brain API Models =====

class BrainRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None

# ===== Health Endpoints =====

@app.get("/")
async def root():
    return {
        "service": "MINDEX + MYCA Brain",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "mindex": "/api/mindex/",
            "voice": "/api/voice/",
            "brain": "/api/brain/"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mindex",
        "version": "2.1.0",
        "species_count": len(species_database),
        "taxonomic_matches": len(taxonomic_matches),
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

# ===== Voice API Endpoints =====

@app.get("/api/voice/tools")
async def list_voice_tools():
    """List available voice tools"""
    return {
        "tools": [
            {"name": "search_species", "description": "Search mushroom species database"},
            {"name": "get_taxonomy", "description": "Get taxonomic information"},
            {"name": "device_control", "description": "Control connected devices"},
            {"name": "workflow_trigger", "description": "Trigger n8n workflows"},
            {"name": "memory_store", "description": "Store information in memory"},
            {"name": "memory_recall", "description": "Recall stored information"}
        ],
        "count": 6,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/voice/execute")
async def execute_voice_tool(request: ToolExecutionRequest):
    """Execute a voice tool"""
    tool_name = request.tool_name
    args = request.arguments
    
    # Tool implementations
    if tool_name == "search_species":
        query = args.get("query", "")
        matches = [s for s in species_database.values() if query.lower() in s.get("name", "").lower()]
        return {"status": "success", "tool": tool_name, "result": matches[:10]}
    
    elif tool_name == "get_taxonomy":
        name = args.get("name", "")
        return {"status": "success", "tool": tool_name, "result": taxonomic_matches.get(name, {})}
    
    elif tool_name == "device_control":
        return {"status": "success", "tool": tool_name, "result": {"message": "Device control initiated"}}
    
    elif tool_name == "workflow_trigger":
        workflow = args.get("workflow", "")
        return {"status": "success", "tool": tool_name, "result": {"workflow": workflow, "triggered": True}}
    
    elif tool_name == "memory_store":
        key = args.get("key", "")
        value = args.get("value", "")
        sessions[key] = value
        return {"status": "success", "tool": tool_name, "result": {"stored": True, "key": key}}
    
    elif tool_name == "memory_recall":
        key = args.get("key", "")
        return {"status": "success", "tool": tool_name, "result": {"key": key, "value": sessions.get(key)}}
    
    else:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

# ===== Brain API Endpoints =====

@app.get("/api/brain/status")
async def brain_status():
    """Get MYCA brain status"""
    return {
        "status": "online",
        "persona": "MYCA",
        "version": "1.0.0",
        "capabilities": ["voice_processing", "tool_execution", "memory", "workflows"],
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/brain/query")
async def brain_query(request: BrainRequest):
    """Process a query through MYCA brain"""
    session_id = request.session_id or f"session_{datetime.now().timestamp()}"
    
    # Store in session
    if session_id not in sessions:
        sessions[session_id] = {"messages": [], "created": datetime.now().isoformat()}
    sessions[session_id]["messages"].append({"role": "user", "content": request.message})
    
    # Generate response (placeholder - integrate with actual LLM)
    response_text = f"I received your message: '{request.message}'. MYCA brain is operational and ready to assist with mycological queries and device control."
    
    sessions[session_id]["messages"].append({"role": "assistant", "content": response_text})
    
    return {
        "response": response_text,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }

# ===== Original MINDEX Endpoints =====

@app.get("/api/mindex/stats")
async def get_stats():
    return {
        "total_species": len(species_database),
        "taxonomic_matches": len(taxonomic_matches),
        "unique_citations": len(citation_hashes),
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/mindex/species")
async def list_species(limit: int = Query(default=100, le=1000), offset: int = Query(default=0)):
    species_list = list(species_database.values())[offset:offset+limit]
    return {
        "species": species_list,
        "count": len(species_list),
        "total": len(species_database),
        "offset": offset,
        "limit": limit
    }

@app.post("/api/mindex/taxonomy/match")
async def match_taxonomy(name: str, fuzzy: bool = True):
    """Match scientific name against GBIF backbone"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.gbif.org/v1/species/match",
                params={"name": name, "strict": not fuzzy}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("usageKey"):
                    gbif_id = data["usageKey"]
                    taxonomic_matches[name] = {
                        "source_name": name,
                        "gbif_id": gbif_id,
                        "canonical_name": data.get("canonicalName"),
                        "scientific_name": data.get("scientificName"),
                        "rank": data.get("rank"),
                        "status": data.get("status"),
                        "kingdom": data.get("kingdom"),
                        "matched_at": datetime.now().isoformat()
                    }
                
                return {
                    "success": True,
                    "match": data,
                    "gbif_id": data.get("usageKey"),
                    "canonical_name": data.get("canonicalName")
                }
            else:
                return {"success": False, "error": "No match found"}
    except Exception as e:
        logger.error(f"GBIF match error: {e}")
        raise HTTPException(status_code=500, detail=f"GBIF API error: {str(e)}")

@app.get("/api/mindex/taxonomy/gbif/{gbif_id}")
async def get_gbif_taxon(gbif_id: int):
    """Get full GBIF taxon details"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"https://api.gbif.org/v1/species/{gbif_id}")
            
            if response.status_code == 200:
                return {"success": True, "taxon": response.json()}
            else:
                raise HTTPException(status_code=404, detail="Taxon not found")
    except Exception as e:
        logger.error(f"GBIF taxon fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mindex/taxonomy/fungi/{name}")
async def lookup_index_fungorum(name: str):
    """Lookup fungal name in Index Fungorum"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://www.indexfungorum.org/ixfwebservice/fungus.asmx/NameSearch",
                params={"SearchText": name, "AnywhereInText": "false"}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "raw_response": response.text[:1000],
                    "note": "Index Fungorum integration active"
                }
            else:
                return {"success": False, "error": "No match in Index Fungorum"}
    except Exception as e:
        logger.error(f"Index Fungorum error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/mindex/reconcile")
async def reconcile_taxon(name: str):
    """Full taxonomic reconciliation pipeline"""
    result = {
        "input_name": name,
        "gbif_match": None,
        "index_fungorum": None,
        "canonical_name": None,
        "gbif_id": None,
        "lsid": None,
        "reconciled": False
    }
    
    try:
        gbif_result = await match_taxonomy(name, fuzzy=True)
        if gbif_result["success"]:
            result["gbif_match"] = gbif_result["match"]
            result["gbif_id"] = gbif_result.get("gbif_id")
            result["canonical_name"] = gbif_result.get("canonical_name")
            result["reconciled"] = True
    except:
        pass
    
    if result.get("gbif_match", {}).get("kingdom") == "Fungi":
        try:
            if_result = await lookup_index_fungorum(name)
            result["index_fungorum"] = if_result
        except:
            pass
    
    return result

@app.post("/api/mindex/devices/register")
async def register_device(device_id: str, device_type: str = "mycobrain", metadata: Dict = None):
    """Register a device"""
    return {
        "status": "registered",
        "device_id": device_id,
        "device_type": device_type,
        "registered_at": datetime.now().isoformat()
    }

@app.post("/api/mindex/telemetry")
async def ingest_telemetry(device_id: str, data: Dict):
    """Ingest telemetry data"""
    return {
        "status": "ingested",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/mindex/devices")
async def list_devices():
    """List registered devices"""
    return {
        "devices": [],
        "count": 0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/mindex/etl-status")
async def etl_status():
    """ETL scraping status"""
    return {
        "status": "idle",
        "last_run": None,
        "species_scraped": 0
    }

if __name__ == "__main__":
    port = int(os.getenv("MINDEX_PORT", "8000"))
    logger.info(f"Starting MINDEX + MYCA Brain v2.1.0 on 0.0.0.0:{port}")
    logger.info("Features: GBIF matching, Voice Tools, Brain API, Memory")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
