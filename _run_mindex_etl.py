"""Run ETL to populate compounds, research papers, and images in MINDEX."""
import paramiko
import textwrap

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

def run(ssh, cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        safe = out[:600].encode("ascii", "replace").decode()
        print(f"  {safe}")
    if err and "warning" not in err.lower() and "notice" not in err.lower():
        safe = err[:300].encode("ascii", "replace").decode()
        print(f"  ERR: {safe}")
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("Connected to MINDEX VM")

# Create the ETL script on the VM
ETL_SCRIPT = textwrap.dedent('''
"""
MINDEX ETL - Populate compounds, research, and images.
Runs directly on the MINDEX VM against the local PostgreSQL.
"""
import psycopg2
import json
import urllib.request
import time

DB = "dbname=mindex user=mycosoft password=REDACTED_DB_PASSWORD host=localhost"

def get_conn():
    return psycopg2.connect(DB)

# =========================================================================
# 1. COMPOUNDS: Fetch from PubChem for top fungal compounds
# =========================================================================
def populate_compounds():
    print("\\n=== POPULATING COMPOUNDS ===")
    conn = get_conn()
    cur = conn.cursor()

    # Check if compounds table has proper columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='compounds'")
    cols = [r[0] for r in cur.fetchall()]
    print(f"  Compounds columns: {cols}")

    # Known fungal compounds to seed
    compounds = [
        {"name": "Psilocybin", "formula": "C12H17N2O4P", "mw": 284.25, "class": "Tryptamine", "bioactivity": ["Psychoactive", "Serotonin receptor agonist"], "cas": "520-52-5"},
        {"name": "Psilocin", "formula": "C12H16N2O", "mw": 204.27, "class": "Tryptamine", "bioactivity": ["Psychoactive", "Serotonin receptor agonist"], "cas": "520-53-6"},
        {"name": "Muscimol", "formula": "C4H6N2O2", "mw": 114.10, "class": "Amino acid derivative", "bioactivity": ["GABA receptor agonist", "Psychoactive"], "cas": "2763-96-4"},
        {"name": "Ibotenic acid", "formula": "C5H6N2O4", "mw": 158.11, "class": "Amino acid", "bioactivity": ["Excitotoxin", "NMDA receptor agonist"], "cas": "2552-55-8"},
        {"name": "Lentinan", "formula": "C42H72O36", "mw": 1153.0, "class": "Beta-glucan", "bioactivity": ["Immunomodulator", "Anti-tumor"], "cas": "37339-90-5"},
        {"name": "Ergothioneine", "formula": "C9H15N3O2S", "mw": 229.30, "class": "Amino acid", "bioactivity": ["Antioxidant", "Cytoprotective"], "cas": "497-30-3"},
        {"name": "Lovastatin", "formula": "C24H36O5", "mw": 404.54, "class": "Statin", "bioactivity": ["HMG-CoA reductase inhibitor", "Cholesterol lowering"], "cas": "75330-75-5"},
        {"name": "Grifolin", "formula": "C22H30O3", "mw": 342.47, "class": "Phenol", "bioactivity": ["Anti-tumor", "Anti-inflammatory"], "cas": "469-38-5"},
        {"name": "Erinacine A", "formula": "C25H36O5", "mw": 416.55, "class": "Diterpenoid", "bioactivity": ["NGF synthesis stimulator", "Neuroprotective"], "cas": "143520-59-8"},
        {"name": "Hericenone C", "formula": "C35H52O5", "mw": 556.78, "class": "Benzaldehyde derivative", "bioactivity": ["NGF synthesis stimulator"], "cas": "147459-77-4"},
        {"name": "Ganoderic acid A", "formula": "C30H44O7", "mw": 516.66, "class": "Triterpenoid", "bioactivity": ["Anti-tumor", "Hepatoprotective"], "cas": "81907-62-2"},
        {"name": "Cordycepin", "formula": "C10H13N5O3", "mw": 251.24, "class": "Nucleoside", "bioactivity": ["Anti-tumor", "Anti-inflammatory", "Immunomodulator"], "cas": "73-03-0"},
        {"name": "Agaritine", "formula": "C12H17N3O4", "mw": 267.28, "class": "Hydrazine derivative", "bioactivity": ["Potentially carcinogenic"], "cas": "2757-90-6"},
        {"name": "Coprine", "formula": "C8H15NO4", "mw": 189.21, "class": "Amino acid derivative", "bioactivity": ["Aldehyde dehydrogenase inhibitor"], "cas": "74299-53-3"},
        {"name": "Laccase", "formula": "", "mw": 0, "class": "Enzyme", "bioactivity": ["Oxidase", "Lignin degradation", "Bioremediation"], "cas": "80498-15-3"},
        {"name": "Amanitin", "formula": "C39H54N10O14S", "mw": 919.0, "class": "Amatoxin", "bioactivity": ["RNA polymerase II inhibitor", "Lethal toxin"], "cas": "23109-05-9"},
        {"name": "Phalloidin", "formula": "C35H48N8O11S", "mw": 788.87, "class": "Phallotoxin", "bioactivity": ["Actin stabilizer", "Cell biology tool"], "cas": "17466-45-4"},
        {"name": "Trehalose", "formula": "C12H22O11", "mw": 342.30, "class": "Disaccharide", "bioactivity": ["Cryoprotectant", "Stress protectant"], "cas": "99-20-7"},
        {"name": "Chitin", "formula": "(C8H13NO5)n", "mw": 0, "class": "Polysaccharide", "bioactivity": ["Structural", "Wound healing"], "cas": "1398-61-4"},
        {"name": "Krestin (PSK)", "formula": "", "mw": 0, "class": "Protein-bound polysaccharide", "bioactivity": ["Immunomodulator", "Anti-tumor"], "cas": "37239-80-0"},
    ]

    inserted = 0
    for c in compounds:
        try:
            cur.execute(
                "INSERT INTO core.compounds (name, formula, molecular_weight, chemical_class, bioactivity, cas_number, source) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (c["name"], c["formula"], c["mw"], c["class"], json.dumps(c["bioactivity"]), c["cas"], "curated")
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"  Error inserting {c['name']}: {e}")
            conn.rollback()
            # Try with simpler insert if columns don't match
            try:
                cur.execute(
                    "INSERT INTO core.compounds (name, formula, molecular_weight, description, source) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (c["name"], c["formula"], c["mw"], f"{c['class']}: {', '.join(c['bioactivity'])}", "curated")
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e2:
                print(f"  Fallback also failed: {e2}")
                conn.rollback()

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} compounds")

# =========================================================================
# 2. RESEARCH: Fetch from PubMed via NCBI E-utilities
# =========================================================================
def populate_research():
    print("\\n=== POPULATING RESEARCH PAPERS ===")
    conn = get_conn()
    cur = conn.cursor()

    # Check columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='research_papers'")
    cols = [r[0] for r in cur.fetchall()]
    print(f"  Research columns: {cols}")

    # Search PubMed for mycology papers
    queries = ["psilocybin mushroom", "Amanita muscaria", "medicinal fungi", "mycelium network", "cordyceps sinensis"]
    inserted = 0

    for query in queries:
        try:
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax=10&retmode=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                ids = data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                continue

            # Fetch details
            detail_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
            req2 = urllib.request.Request(detail_url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                details = json.loads(resp2.read())

            for pmid in ids:
                info = details.get("result", {}).get(pmid, {})
                if not info or not isinstance(info, dict):
                    continue
                title = info.get("title", "")
                authors = [a.get("name", "") for a in info.get("authors", [])]
                journal = info.get("source", "")
                year = int(info.get("pubdate", "0")[:4]) if info.get("pubdate", "")[:4].isdigit() else 0
                doi = ""
                for artid in info.get("articleids", []):
                    if artid.get("idtype") == "doi":
                        doi = artid.get("value", "")
                        break

                try:
                    cur.execute(
                        "INSERT INTO core.research_papers (title, authors, journal, year, doi, source, pubmed_id) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (title, json.dumps(authors), journal, year, doi, "pubmed", pmid)
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    # Try simpler insert
                    try:
                        cur.execute(
                            "INSERT INTO core.research_papers (title, abstract, source) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                            (title, f"Authors: {', '.join(authors[:3])}. Journal: {journal}. Year: {year}. DOI: {doi}", "pubmed")
                        )
                        if cur.rowcount > 0:
                            inserted += 1
                    except:
                        conn.rollback()

            time.sleep(0.5)  # Rate limit
        except Exception as e:
            print(f"  Error querying PubMed for '{query}': {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} research papers")

# =========================================================================
# 3. IMAGES: Backfill species_images from iNaturalist using inat_id
# =========================================================================
def backfill_images():
    print("\\n=== BACKFILLING SPECIES IMAGES ===")
    conn = get_conn()
    cur = conn.cursor()

    # Get taxa with inat_id but no images
    cur.execute("SELECT id, inat_id, scientific_name FROM core.taxon WHERE inat_id IS NOT NULL ORDER BY id LIMIT 500")
    taxa = cur.fetchall()
    print(f"  Found {len(taxa)} taxa with inat_ids to process")

    # Check species_images columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='species_images'")
    cols = [r[0] for r in cur.fetchall()]
    print(f"  species_images columns: {cols}")

    inserted = 0
    for taxon_id, inat_id, sci_name in taxa[:200]:  # Process first 200
        try:
            url = f"https://api.inaturalist.org/v1/taxa/{inat_id}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())

            results = data.get("results", [])
            if not results:
                continue

            taxon_data = results[0]
            photos = taxon_data.get("taxon_photos", [])
            if not photos:
                dp = taxon_data.get("default_photo")
                if dp:
                    photos = [{"photo": dp}]

            for p in photos[:5]:
                photo = p.get("photo", {})
                photo_url = photo.get("medium_url") or photo.get("url", "")
                if not photo_url:
                    continue
                try:
                    cur.execute(
                        "INSERT INTO core.species_images (taxon_id, image_url, source, attribution) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (taxon_id, photo_url, "inaturalist", photo.get("attribution", "iNaturalist"))
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    conn.rollback()

            time.sleep(0.3)  # Rate limit
        except Exception as e:
            pass  # Silently skip failures

        if inserted > 0 and inserted % 50 == 0:
            conn.commit()
            print(f"  ... {inserted} images so far")

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} species images")


if __name__ == "__main__":
    import urllib.parse
    populate_compounds()
    populate_research()
    backfill_images()
    print("\\n=== ALL ETL COMPLETE ===")
''').strip()

print("\n[1] Writing ETL script to VM...")
sftp = ssh.open_sftp()
with sftp.file("/opt/mycosoft/mindex/run_etl.py", "w") as f:
    f.write(ETL_SCRIPT)
sftp.close()
print("  Written to /opt/mycosoft/mindex/run_etl.py")

print("\n[2] Running ETL (this may take a few minutes)...")
out, err = run(ssh, "cd /opt/mycosoft/mindex && /opt/mycosoft/mindex/venv/bin/python run_etl.py", timeout=300)

print("\n[3] Checking final counts...")
for table in ["core.compounds", "core.research_papers", "core.species_images"]:
    out2, _ = run(ssh, f"docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT COUNT(*) FROM {table};\" 2>/dev/null")
    lines = out2.strip().split('\n')
    count = lines[2].strip() if len(lines) > 2 else "N/A"
    print(f"  {table}: {count}")

ssh.close()
print("\n=== DONE ===")
