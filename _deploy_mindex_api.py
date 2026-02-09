"""Deploy MINDEX API to VM 189 via SSH."""
import paramiko
import textwrap

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(f"  OUT: {out[:500].encode('ascii', 'replace').decode()}")
    if err and "WARNING" not in err.upper():
        print(f"  ERR: {err[:300].encode('ascii', 'replace').decode()}")
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("Connected to MINDEX VM")

# Step 1: Install dependencies
print("\n[1] Installing Python dependencies...")
run(ssh, "sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv 2>/dev/null", timeout=60)
run(ssh, "python3 -m venv /opt/mycosoft/mindex/venv 2>/dev/null || true", timeout=30)
run(ssh, "/opt/mycosoft/mindex/venv/bin/pip install fastapi uvicorn psycopg2-binary 2>/dev/null", timeout=60)

# Step 2: Create the API file
print("\n[2] Creating MINDEX API...")

API_CODE = textwrap.dedent('''
"""
MINDEX API - Feb 2026
FastAPI service querying real MINDEX PostgreSQL database.
Serves species, compounds, sequences, research from core schema.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional
import json

app = FastAPI(title="MINDEX API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "mindex",
    "user": "mycosoft",
    "password": "REDACTED_DB_PASSWORD",
}

@contextmanager
def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def row_to_dict(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


@app.get("/health")
def health():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "service": "mindex-api", "database": "connected"}
    except Exception as e:
        return {"status": "error", "service": "mindex-api", "error": str(e)}


@app.get("/mindex/stats")
def stats():
    with get_db() as conn:
        with conn.cursor() as cur:
            counts = {}
            for table in ["core.taxon", "core.compounds", "core.dna_sequences", "core.research_papers", "core.species_images"]:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
                except:
                    counts[table] = 0
                    conn.rollback()
            return {"tables": counts, "status": "live"}


@app.get("/mindex/species/search")
def species_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, scientific_name, canonical_name, common_name,
                       kingdom, phylum, class_name, order_name, family, genus, species,
                       rank, description, habitat, edibility,
                       inat_id, gbif_key, source, source_url,
                       common_names, metadata
                FROM core.taxon
                WHERE scientific_name ILIKE %s
                   OR common_name ILIKE %s
                   OR %s = ANY(common_names)
                ORDER BY
                    CASE WHEN scientific_name ILIKE %s THEN 0
                         WHEN common_name ILIKE %s THEN 1
                         ELSE 2 END,
                    scientific_name
                LIMIT %s OFFSET %s
            """, (
                f"%{q}%", f"%{q}%", q.lower(),
                f"{q}%", f"{q}%",
                limit, offset
            ))
            rows = cur.fetchall()

            results = []
            for r in rows:
                # Build photo URL from iNaturalist ID if available
                photos = []
                if r.get("inat_id"):
                    inat_id = r["inat_id"]
                    photos.append({
                        "id": str(inat_id),
                        "url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{inat_id}/medium.jpg",
                        "medium_url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{inat_id}/medium.jpg",
                        "large_url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{inat_id}/large.jpg",
                        "attribution": "iNaturalist",
                    })

                habitat = r.get("habitat") or []
                if isinstance(habitat, str):
                    try:
                        habitat = json.loads(habitat)
                    except:
                        habitat = [habitat] if habitat else []

                results.append({
                    "id": str(r["id"]),
                    "scientificName": r.get("scientific_name", ""),
                    "commonName": r.get("common_name", "") or r.get("canonical_name", ""),
                    "taxonomy": {
                        "kingdom": r.get("kingdom", "") or "Fungi",
                        "phylum": r.get("phylum", "") or "",
                        "class": r.get("class_name", "") or "",
                        "order": r.get("order_name", "") or "",
                        "family": r.get("family", "") or "",
                        "genus": r.get("genus", "") or "",
                    },
                    "description": r.get("description", "") or "",
                    "photos": photos,
                    "observationCount": 0,
                    "rank": r.get("rank", "species") or "species",
                    "habitat": habitat,
                    "edibility": r.get("edibility", "") or "",
                    "inatId": r.get("inat_id"),
                    "gbifKey": r.get("gbif_key"),
                    "_source": "MINDEX",
                })

            return {"results": results, "total": len(results), "query": q}


@app.get("/mindex/species/{species_id}")
def species_by_id(species_id: int):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM core.taxon WHERE id = %s", (species_id,))
            r = cur.fetchone()
            if not r:
                return {"error": "Species not found"}
            return dict(r)


@app.get("/mindex/compounds/search")
def compounds_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM core.compounds
                WHERE name ILIKE %s OR formula ILIKE %s
                ORDER BY name LIMIT %s
            """, (f"%{q}%", f"%{q}%", limit))
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": str(r.get("id", "")),
                    "name": r.get("name", ""),
                    "formula": r.get("formula", ""),
                    "molecularWeight": r.get("molecular_weight", 0) or 0,
                    "chemicalClass": r.get("chemical_class", "") or "",
                    "sourceSpecies": [],
                    "biologicalActivity": r.get("bioactivity", []) or [],
                    "_source": "MINDEX",
                })
            return {"results": results, "total": len(results), "query": q}


@app.get("/mindex/sequences/search")
def sequences_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT s.*, t.scientific_name, t.common_name
                FROM core.dna_sequences s
                LEFT JOIN core.taxon t ON s.taxon_id = t.id
                WHERE t.scientific_name ILIKE %s OR t.common_name ILIKE %s
                ORDER BY s.id LIMIT %s
            """, (f"%{q}%", f"%{q}%", limit))
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": str(r.get("id", "")),
                    "accession": r.get("accession_number", "") or "",
                    "speciesName": r.get("scientific_name", "") or "",
                    "geneRegion": r.get("sequence_type", "") or "ITS",
                    "sequenceLength": r.get("length", 0) or 0,
                    "gcContent": None,
                    "source": "MINDEX",
                    "_source": "MINDEX",
                })
            return {"results": results, "total": len(results), "query": q}


@app.get("/mindex/research/search")
def research_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM core.research_papers
                WHERE title ILIKE %s OR abstract ILIKE %s
                ORDER BY id LIMIT %s
            """, (f"%{q}%", f"%{q}%", limit))
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": str(r.get("id", "")),
                    "title": r.get("title", ""),
                    "authors": r.get("authors", []) or [],
                    "journal": r.get("journal", "") or "",
                    "year": r.get("year", 0) or 0,
                    "doi": r.get("doi", "") or "",
                    "abstract": r.get("abstract", "") or "",
                    "relatedSpecies": [],
                    "_source": "MINDEX",
                })
            return {"results": results, "total": len(results), "query": q}


@app.get("/mindex/unified/search")
def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    include_species: bool = Query(True),
    include_compounds: bool = Query(True),
    include_sequences: bool = Query(True),
    include_research: bool = Query(True),
):
    results = {}
    if include_species:
        results["species"] = species_search(q=q, limit=limit).get("results", [])
    if include_compounds:
        results["compounds"] = compounds_search(q=q, limit=limit).get("results", [])
    if include_sequences:
        results["genetics"] = sequences_search(q=q, limit=limit).get("results", [])
    if include_research:
        results["research"] = research_search(q=q, limit=limit).get("results", [])

    total = sum(len(v) for v in results.values())
    return {"query": q, "results": results, "totalCount": total, "source": "MINDEX"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''').strip()

# Write the API file
sftp = ssh.open_sftp()
with sftp.file("/opt/mycosoft/mindex/api.py", "w") as f:
    f.write(API_CODE)
sftp.close()
print("  API file written to /opt/mycosoft/mindex/api.py")

# Step 3: Create systemd service
print("\n[3] Creating systemd service...")
SERVICE = textwrap.dedent('''
[Unit]
Description=MINDEX API Service
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=mycosoft
WorkingDirectory=/opt/mycosoft/mindex
ExecStart=/opt/mycosoft/mindex/venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
''').strip()

# Write service file via sudo
run(ssh, f"echo '{SERVICE}' | sudo tee /etc/systemd/system/mindex-api.service > /dev/null")
print("  Service file created")

# Step 4: Enable and start the service
print("\n[4] Starting MINDEX API service...")
run(ssh, "sudo systemctl daemon-reload")
run(ssh, "sudo systemctl enable mindex-api")
run(ssh, "sudo systemctl restart mindex-api")

import time
time.sleep(3)

# Step 5: Verify
print("\n[5] Verifying MINDEX API...")
out, err = run(ssh, "sudo systemctl status mindex-api --no-pager | head -15")
out2, _ = run(ssh, "curl -s http://localhost:8000/health 2>/dev/null || echo 'NOT RESPONDING'")
print(f"\n  Health check: {out2}")
out3, _ = run(ssh, "curl -s 'http://localhost:8000/mindex/species/search?q=amanita&limit=2' 2>/dev/null | head -c 500")
print(f"\n  Species search test: {out3[:500]}")

ssh.close()
print("\n=== DEPLOYMENT COMPLETE ===")
