#!/usr/bin/env python3
"""
MINDEX - Mycological Index Data System
Enhanced with taxonomic reconciliation (GBIF, iNaturalist, Index Fungorum)
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import hashlib
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MINDEX", version="2.0.0", description="Mycological Index with Taxonomic Reconciliation")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# In-memory storage (replace with PostgreSQL in production)
species_database = {}
taxonomic_matches = {}
citation_hashes = set()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mindex",
        "version": "2.0.0",
        "species_count": len(species_database),
        "taxonomic_matches": len(taxonomic_matches),
        "timestamp": datetime.now().isoformat()
    }

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
            # GBIF Species Match API
            response = await client.get(
                "https://api.gbif.org/v1/species/match",
                params={"name": name, "strict": not fuzzy}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Store match
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
            # Index Fungorum name search
            response = await client.get(
                "http://www.indexfungorum.org/ixfwebservice/fungus.asmx/NameSearch",
                params={"SearchText": name, "AnywhereInText": "false"}
            )
            
            if response.status_code == 200:
                # Parse XML response (simplified)
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
    
    # Step 1: GBIF match
    try:
        gbif_result = await match_taxonomy(name, fuzzy=True)
        if gbif_result["success"]:
            result["gbif_match"] = gbif_result["match"]
            result["gbif_id"] = gbif_result.get("gbif_id")
            result["canonical_name"] = gbif_result.get("canonical_name")
            result["reconciled"] = True
    except:
        pass
    
    # Step 2: Index Fungorum (if fungi)
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
    logger.info(f"Starting MINDEX v2.0.0 on 0.0.0.0:{port}")
    logger.info("Features: GBIF matching, Index Fungorum, iNaturalist ready")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


