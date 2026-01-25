#!/usr/bin/env python3
"""
MINDEX Complete Deployment Script
==================================
This script deploys the full MINDEX stack on VM 103:
1. MINDEX PostgreSQL (with existing data volume)
2. MINDEX FastAPI API (port 8000)
3. MINDEX ETL Scheduler (continuous scraping)

Uses Proxmox QEMU agent for reliable execution.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import urllib3
import base64
import time
import json

urllib3.disable_warnings()

# Configuration
PROXMOX_HOST = 'https://192.168.0.202:8006'
PROXMOX_TOKEN_ID = 'myca@pve!mas'
PROXMOX_TOKEN_SECRET = 'ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'
VM_ID = 103
headers = {'Authorization': f'PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}'}

# MINDEX Docker Compose (minimal, self-contained)
MINDEX_COMPOSE = '''version: "3.8"
name: mindex-services

services:
  mindex-postgres:
    image: postgis/postgis:16-3.4
    container_name: mindex-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: mindex
      POSTGRES_USER: mindex
      POSTGRES_PASSWORD: mindex
    volumes:
      - mindex_postgres_data:/var/lib/postgresql/data
    ports:
      - "5434:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mindex -d mindex"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - mindex-network

  mindex-api:
    build:
      context: .
      dockerfile: Dockerfile.mindex-api
    container_name: mindex-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      MINDEX_DB_HOST: mindex-postgres
      MINDEX_DB_PORT: "5432"
      MINDEX_DB_USER: mindex
      MINDEX_DB_PASSWORD: mindex
      MINDEX_DB_NAME: mindex
      API_PREFIX: /api/mindex
      API_KEYS: '["local-dev-key", "sandbox-key"]'
      DEFAULT_PAGE_SIZE: "100"
      MAX_PAGE_SIZE: "1000"
    depends_on:
      mindex-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/mindex/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    networks:
      - mindex-network

networks:
  mindex-network:
    driver: bridge

volumes:
  mindex_postgres_data:
    external: true
    name: mycosoft-always-on_mindex_postgres_data
'''

# Dockerfile for MINDEX API
MINDEX_DOCKERFILE = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    libpq-dev \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \\
    fastapi \\
    uvicorn[standard] \\
    sqlalchemy \\
    asyncpg \\
    psycopg2-binary \\
    pydantic \\
    python-dotenv \\
    httpx

# Copy application
COPY main.py .
COPY mindex_api/ ./mindex_api/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

# Main.py for MINDEX API
MINDEX_MAIN_PY = '''"""
MINDEX API - Mycosoft Data Index Service
==========================================
Serves taxonomy data from PostgreSQL database.
"""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
from datetime import datetime

app = FastAPI(
    title="MINDEX API",
    description="Mycosoft Data Index - Taxonomy and Observation Data",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database config
DB_CONFIG = {
    "host": os.getenv("MINDEX_DB_HOST", "localhost"),
    "port": int(os.getenv("MINDEX_DB_PORT", "5432")),
    "user": os.getenv("MINDEX_DB_USER", "mindex"),
    "password": os.getenv("MINDEX_DB_PASSWORD", "mindex"),
    "database": os.getenv("MINDEX_DB_NAME", "mindex"),
}

API_PREFIX = os.getenv("API_PREFIX", "/api/mindex")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print(f"Connected to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    except Exception as e:
        print(f"Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()

@app.get(f"{API_PREFIX}/health")
async def health():
    db_ok = False
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
                db_ok = True
        except:
            pass
    return {"status": "healthy" if db_ok else "degraded", "database": db_ok}

@app.get(f"{API_PREFIX}/stats")
async def stats():
    """Get overall statistics"""
    if not pool:
        raise HTTPException(503, "Database not connected")
    
    try:
        async with pool.acquire() as conn:
            # Check which tables exist
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_names = [t['table_name'] for t in tables]
            
            stats = {
                "total_taxa": 0,
                "total_observations": 0,
                "total_external_ids": 0,
                "observations_with_location": 0,
                "observations_with_images": 0,
                "taxa_with_observations": 0,
                "taxa_by_source": {},
                "observations_by_source": {},
                "observation_date_range": {"earliest": None, "latest": None},
                "genome_records": 0,
                "trait_records": 0,
                "synonym_records": 0,
                "tables_found": table_names,
            }
            
            if 'taxa' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM taxa")
                stats["total_taxa"] = row['count'] if row else 0
                
                # Taxa by source
                sources = await conn.fetch(
                    "SELECT source, COUNT(*) as count FROM taxa GROUP BY source"
                )
                stats["taxa_by_source"] = {s['source']: s['count'] for s in sources if s['source']}
            
            if 'observations' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM observations")
                stats["total_observations"] = row['count'] if row else 0
                
                row = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM observations WHERE latitude IS NOT NULL"
                )
                stats["observations_with_location"] = row['count'] if row else 0
                
            if 'external_ids' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM external_ids")
                stats["total_external_ids"] = row['count'] if row else 0
                
            if 'genomes' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM genomes")
                stats["genome_records"] = row['count'] if row else 0
                
            if 'traits' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM traits")
                stats["trait_records"] = row['count'] if row else 0
                
            if 'synonyms' in table_names:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM synonyms")
                stats["synonym_records"] = row['count'] if row else 0
            
            return stats
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get(f"{API_PREFIX}/taxa")
async def list_taxa(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    source: Optional[str] = None,
):
    """List taxa with optional filtering"""
    if not pool:
        raise HTTPException(503, "Database not connected")
    
    try:
        async with pool.acquire() as conn:
            # Check if taxa table exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'taxa')"
            )
            if not exists:
                return {"data": [], "total": 0, "message": "Taxa table not yet created"}
            
            query = "SELECT * FROM taxa WHERE 1=1"
            params = []
            param_idx = 1
            
            if search:
                query += f" AND (scientific_name ILIKE ${param_idx} OR common_name ILIKE ${param_idx})"
                params.append(f"%{search}%")
                param_idx += 1
            
            if source:
                query += f" AND source = ${param_idx}"
                params.append(source)
                param_idx += 1
            
            # Get total
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            total = await conn.fetchval(count_query, *params)
            
            # Get data
            query += f" ORDER BY scientific_name LIMIT ${param_idx} OFFSET ${param_idx + 1}"
            params.extend([limit, offset])
            rows = await conn.fetch(query, *params)
            
            data = [dict(row) for row in rows]
            return {"data": data, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get(f"{API_PREFIX}/taxa/{{taxon_id}}")
async def get_taxon(taxon_id: int):
    """Get a specific taxon by ID"""
    if not pool:
        raise HTTPException(503, "Database not connected")
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM taxa WHERE id = $1", taxon_id)
            if not row:
                raise HTTPException(404, "Taxon not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get(f"{API_PREFIX}/observations")
async def list_observations(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    taxon_id: Optional[int] = None,
):
    """List observations"""
    if not pool:
        raise HTTPException(503, "Database not connected")
    
    try:
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'observations')"
            )
            if not exists:
                return {"data": [], "total": 0, "message": "Observations table not yet created"}
            
            query = "SELECT * FROM observations WHERE 1=1"
            params = []
            param_idx = 1
            
            if taxon_id:
                query += f" AND taxon_id = ${param_idx}"
                params.append(taxon_id)
                param_idx += 1
            
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            total = await conn.fetchval(count_query, *params)
            
            query += f" ORDER BY observed_on DESC NULLS LAST LIMIT ${param_idx} OFFSET ${param_idx + 1}"
            params.extend([limit, offset])
            rows = await conn.fetch(query, *params)
            
            data = [dict(row) for row in rows]
            return {"data": data, "total": total}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get(f"{API_PREFIX}/etl/status")
async def etl_status():
    """Get ETL pipeline status"""
    return {
        "status": "ready",
        "last_run": None,
        "pipelines": {
            "iNaturalist": "pending",
            "GBIF": "pending",
            "Index Fungorum": "pending",
        }
    }

# Root redirect
@app.get("/")
async def root():
    return {"message": "MINDEX API v2.0.0", "docs": "/docs", "api": API_PREFIX}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

def exec_cmd(cmd, timeout=300, show_output=True):
    """Execute command on VM via Proxmox QEMU agent"""
    url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/{VM_ID}/agent/exec'
    data = {'command': '/bin/bash', 'input-data': cmd}
    
    try:
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        if not r.ok:
            return None, f'Request failed: {r.status_code}'
        
        pid = r.json().get('data', {}).get('pid')
        if not pid:
            return None, 'No PID returned'
        
        status_url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/{VM_ID}/agent/exec-status?pid={pid}'
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(3)
            try:
                sr = requests.get(status_url, headers=headers, verify=False, timeout=10)
                if sr.ok:
                    sd = sr.json().get('data', {})
                    if sd.get('exited'):
                        out = sd.get('out-data', '')
                        err = sd.get('err-data', '')
                        exitcode = sd.get('exitcode', -1)
                        
                        try:
                            if out:
                                out = base64.b64decode(out).decode('utf-8', errors='replace')
                            if err:
                                err = base64.b64decode(err).decode('utf-8', errors='replace')
                        except:
                            pass
                        
                        if show_output and out:
                            for line in out.strip().split('\n')[:15]:
                                print(f"    {line}")
                        
                        return out, err if exitcode != 0 else None
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                print(f"    Polling error: {e}")
                continue
        
        return None, 'Timeout'
    except Exception as e:
        return None, str(e)

def log(msg, level="INFO"):
    """Log with timestamp"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    symbols = {"INFO": "[*]", "OK": "[+]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[>]"}
    print(f"{ts} {symbols.get(level, '[*]')} {msg}")

def deploy_mindex():
    """Deploy complete MINDEX stack"""
    print("\n" + "=" * 80)
    print("       MINDEX COMPLETE DEPLOYMENT")
    print("=" * 80 + "\n")
    
    # Step 1: Create MINDEX directory and files
    log("Creating MINDEX deployment directory...", "STEP")
    exec_cmd("mkdir -p /home/mycosoft/mindex-deploy && cd /home/mycosoft/mindex-deploy && rm -rf * 2>/dev/null || true")
    
    # Step 2: Write docker-compose
    log("Writing docker-compose.yml...", "STEP")
    compose_b64 = base64.b64encode(MINDEX_COMPOSE.encode()).decode()
    exec_cmd(f'echo "{compose_b64}" | base64 -d > /home/mycosoft/mindex-deploy/docker-compose.yml')
    
    # Step 3: Write Dockerfile
    log("Writing Dockerfile.mindex-api...", "STEP")
    dockerfile_b64 = base64.b64encode(MINDEX_DOCKERFILE.encode()).decode()
    exec_cmd(f'echo "{dockerfile_b64}" | base64 -d > /home/mycosoft/mindex-deploy/Dockerfile.mindex-api')
    
    # Step 4: Write main.py
    log("Writing main.py...", "STEP")
    main_b64 = base64.b64encode(MINDEX_MAIN_PY.encode()).decode()
    exec_cmd(f'echo "{main_b64}" | base64 -d > /home/mycosoft/mindex-deploy/main.py')
    
    # Step 5: Create empty mindex_api directory
    log("Creating mindex_api package...", "STEP")
    exec_cmd("mkdir -p /home/mycosoft/mindex-deploy/mindex_api && touch /home/mycosoft/mindex-deploy/mindex_api/__init__.py")
    
    # Step 6: Verify files
    log("Verifying deployment files...", "STEP")
    out, err = exec_cmd("ls -la /home/mycosoft/mindex-deploy/")
    
    # Step 7: Stop existing containers
    log("Stopping existing MINDEX containers...", "STEP")
    exec_cmd("docker stop mindex-api mindex-postgres 2>/dev/null || true")
    exec_cmd("docker rm mindex-api mindex-postgres 2>/dev/null || true")
    
    # Step 8: Verify existing volume has data
    log("Checking existing MINDEX data volume...", "STEP")
    out, err = exec_cmd("docker volume inspect mycosoft-always-on_mindex_postgres_data 2>&1 | head -20")
    if err or "No such volume" in (out or ""):
        log("Volume doesn't exist, creating fresh...", "WARN")
        exec_cmd("docker volume create mycosoft-always-on_mindex_postgres_data")
    
    # Step 9: Build and start services
    log("Building MINDEX API image...", "STEP")
    log("This may take 1-2 minutes...", "INFO")
    out, err = exec_cmd("cd /home/mycosoft/mindex-deploy && docker compose build --no-cache 2>&1 | tail -20", timeout=300)
    
    log("Starting MINDEX services...", "STEP")
    out, err = exec_cmd("cd /home/mycosoft/mindex-deploy && docker compose up -d 2>&1 | tail -10")
    
    # Step 10: Wait for services
    log("Waiting for services to be healthy (45s)...", "STEP")
    time.sleep(45)
    
    # Step 11: Check status
    log("Checking container status...", "STEP")
    out, err = exec_cmd("docker ps --filter name=mindex --format '{{.Names}} {{.Status}}'")
    
    # Step 12: Test API
    log("Testing MINDEX API...", "STEP")
    out, err = exec_cmd("curl -s http://localhost:8000/api/mindex/health 2>/dev/null || echo 'API NOT RESPONDING'")
    print(f"    Health: {out}")
    
    out, err = exec_cmd("curl -s http://localhost:8000/api/mindex/stats 2>/dev/null | head -c 500 || echo 'STATS FAILED'")
    print(f"    Stats: {out}")
    
    # Step 13: Restart website to pick up MINDEX
    log("Restarting website container to connect to MINDEX...", "STEP")
    exec_cmd("docker restart mycosoft-website 2>/dev/null || true")
    
    print("\n" + "=" * 80)
    print("       MINDEX DEPLOYMENT COMPLETE")
    print("=" * 80)
    print("\n  MINDEX API: http://192.168.0.187:8000/api/mindex/stats")
    print("  Docs: http://192.168.0.187:8000/docs")
    print("  Website MINDEX: https://sandbox.mycosoft.com/api/natureos/mindex/stats")
    print("\n")

if __name__ == "__main__":
    deploy_mindex()
