"""Final ETL with correct column names."""
import paramiko, textwrap

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

def run(ssh, cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("Connected to MINDEX VM")

SCRIPT = textwrap.dedent(r'''
import psycopg2, json, urllib.request, urllib.parse, time

DB = "dbname=mindex user=mycosoft password=REDACTED_DB_PASSWORD host=localhost"

def get_conn():
    return psycopg2.connect(DB)

# === COMPOUNDS ===
def populate_compounds():
    print("\n=== COMPOUNDS ===")
    conn = get_conn()
    cur = conn.cursor()
    compounds = [
        ("Psilocybin", "C12H17N2O4P", 284.25, "Tryptamine", ["Psychoactive","Serotonin receptor agonist"], "520-52-5", ["Psilocybe cubensis","Psilocybe semilanceata"]),
        ("Psilocin", "C12H16N2O", 204.27, "Tryptamine", ["Psychoactive","Serotonin receptor agonist"], "520-53-6", ["Psilocybe cubensis"]),
        ("Muscimol", "C4H6N2O2", 114.10, "Amino acid derivative", ["GABA receptor agonist","Psychoactive"], "2763-96-4", ["Amanita muscaria"]),
        ("Ibotenic acid", "C5H6N2O4", 158.11, "Amino acid", ["Excitotoxin","NMDA receptor agonist"], "2552-55-8", ["Amanita muscaria","Amanita pantherina"]),
        ("Lentinan", "C42H72O36", 1153.0, "Beta-glucan", ["Immunomodulator","Anti-tumor"], "37339-90-5", ["Lentinula edodes"]),
        ("Ergothioneine", "C9H15N3O2S", 229.30, "Amino acid", ["Antioxidant","Cytoprotective"], "497-30-3", ["Pleurotus ostreatus","Lentinula edodes"]),
        ("Lovastatin", "C24H36O5", 404.54, "Statin", ["HMG-CoA reductase inhibitor"], "75330-75-5", ["Pleurotus ostreatus"]),
        ("Grifolin", "C22H30O3", 342.47, "Phenol", ["Anti-tumor","Anti-inflammatory"], "469-38-5", ["Albatrellus confluens"]),
        ("Erinacine A", "C25H36O5", 416.55, "Diterpenoid", ["NGF synthesis stimulator","Neuroprotective"], "143520-59-8", ["Hericium erinaceus"]),
        ("Hericenone C", "C35H52O5", 556.78, "Benzaldehyde derivative", ["NGF synthesis stimulator"], "147459-77-4", ["Hericium erinaceus"]),
        ("Ganoderic acid A", "C30H44O7", 516.66, "Triterpenoid", ["Anti-tumor","Hepatoprotective"], "81907-62-2", ["Ganoderma lucidum"]),
        ("Cordycepin", "C10H13N5O3", 251.24, "Nucleoside", ["Anti-tumor","Anti-inflammatory","Immunomodulator"], "73-03-0", ["Cordyceps militaris"]),
        ("Agaritine", "C12H17N3O4", 267.28, "Hydrazine derivative", ["Potentially carcinogenic"], "2757-90-6", ["Agaricus bisporus"]),
        ("Coprine", "C8H15NO4", 189.21, "Amino acid derivative", ["Aldehyde dehydrogenase inhibitor"], "74299-53-3", ["Coprinopsis atramentaria"]),
        ("Alpha-amanitin", "C39H54N10O14S", 919.0, "Amatoxin", ["RNA polymerase II inhibitor","Lethal toxin"], "23109-05-9", ["Amanita phalloides"]),
        ("Phalloidin", "C35H48N8O11S", 788.87, "Phallotoxin", ["Actin stabilizer"], "17466-45-4", ["Amanita phalloides"]),
        ("Trehalose", "C12H22O11", 342.30, "Disaccharide", ["Cryoprotectant","Stress protectant"], "99-20-7", ["Multiple fungi"]),
        ("Krestin", "", 0, "Protein-bound polysaccharide", ["Immunomodulator","Anti-tumor"], "37239-80-0", ["Trametes versicolor"]),
        ("Schizophyllan", "(C6H10O5)n", 0, "Beta-glucan", ["Immunomodulator","Anti-tumor"], "9050-67-3", ["Schizophyllum commune"]),
        ("Hispidin", "C13H10O5", 246.22, "Polyphenol", ["Antioxidant","Anti-diabetic"], "10048-32-5", ["Inonotus hispidus"]),
    ]
    inserted = 0
    for name, formula, mw, cls, bio, cas, species in compounds:
        try:
            cur.execute(
                """INSERT INTO core.compounds (name, molecular_formula, molecular_weight, compound_class, bioactivity, cas_number, producing_species, source)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (name, formula, mw if mw > 0 else None, cls, json.dumps(bio), cas, species, "curated")
            )
            if cur.rowcount > 0: inserted += 1
        except Exception as e:
            print(f"  ERR {name}: {e}")
            conn.rollback()
    conn.commit()
    conn.close()
    print(f"  Inserted {inserted} compounds")

# === RESEARCH PAPERS ===
def populate_research():
    print("\n=== RESEARCH PAPERS ===")
    conn = get_conn()
    cur = conn.cursor()
    queries = ["psilocybin mushroom", "Amanita muscaria toxin", "medicinal fungi beta glucan", "mycelium network communication", "cordyceps sinensis medicinal"]
    inserted = 0
    for query in queries:
        try:
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax=10&retmode=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            ids = data.get("esearchresult", {}).get("idlist", [])
            if not ids: continue

            detail_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
            req2 = urllib.request.Request(detail_url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                details = json.loads(resp2.read())

            for pmid in ids:
                info = details.get("result", {}).get(pmid, {})
                if not isinstance(info, dict): continue
                title = info.get("title", "")
                authors = json.dumps([a.get("name", "") for a in info.get("authors", [])])
                journal = info.get("source", "")
                year_str = info.get("pubdate", "")[:4]
                year = int(year_str) if year_str.isdigit() else 0
                doi = ""
                for artid in info.get("articleids", []):
                    if artid.get("idtype") == "doi":
                        doi = artid.get("value", "")
                        break
                try:
                    cur.execute(
                        """INSERT INTO core.research_papers (pmid, title, authors, journal, year, doi, source)
                           VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (pmid, title, authors, journal, year, doi, "pubmed")
                    )
                    if cur.rowcount > 0: inserted += 1
                except Exception as e:
                    conn.rollback()
            time.sleep(0.4)
        except Exception as e:
            print(f"  ERR {query}: {e}")
    conn.commit()
    conn.close()
    print(f"  Inserted {inserted} research papers")

# === IMAGES (record inat_id for linking, not blobs) ===
def backfill_images():
    print("\n=== SPECIES IMAGES ===")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, inat_id, scientific_name FROM core.taxon WHERE inat_id IS NOT NULL ORDER BY id LIMIT 100")
    taxa = cur.fetchall()
    print(f"  Processing {len(taxa)} taxa")
    inserted = 0
    for taxon_id, inat_id, sci_name in taxa:
        try:
            url = f"https://api.inaturalist.org/v1/taxa/{inat_id}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mycosoft/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            results = data.get("results", [])
            if not results: continue
            taxon_data = results[0]
            photos = taxon_data.get("taxon_photos", [])
            if not photos:
                dp = taxon_data.get("default_photo")
                if dp: photos = [{"photo": dp}]
            for p in photos[:3]:
                photo = p.get("photo", {})
                attribution = photo.get("attribution", "iNaturalist")
                license_code = photo.get("license_code", "")
                try:
                    cur.execute(
                        """INSERT INTO core.species_images (taxon_id, inat_id, scientific_name, attribution, license, is_primary)
                           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (taxon_id, inat_id, sci_name, attribution, license_code, photos.index(p) == 0)
                    )
                    if cur.rowcount > 0: inserted += 1
                except: conn.rollback()
            time.sleep(0.35)
        except: pass
        if inserted and inserted % 20 == 0:
            conn.commit()
            print(f"  ... {inserted} images")
    conn.commit()
    conn.close()
    print(f"  Inserted {inserted} image records")

if __name__ == "__main__":
    populate_compounds()
    populate_research()
    backfill_images()
    print("\n=== ALL DONE ===")
''').strip()

print("[1] Writing ETL script...")
sftp = ssh.open_sftp()
with sftp.file("/opt/mycosoft/mindex/run_etl_v2.py", "w") as f:
    f.write(SCRIPT)
sftp.close()

print("[2] Running ETL...")
out, err = run(ssh, "cd /opt/mycosoft/mindex && /opt/mycosoft/mindex/venv/bin/python run_etl_v2.py 2>&1", timeout=300)
print(out[:2000] if out else "No output")
if err:
    print(f"ERR: {err[:500]}")

print("\n[3] Final counts...")
for t in ["core.compounds", "core.research_papers", "core.species_images"]:
    o, _ = run(ssh, f"docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT COUNT(*) FROM {t};\" 2>/dev/null")
    lines = o.strip().split('\n')
    count = lines[2].strip() if len(lines) > 2 else "?"
    print(f"  {t}: {count}")

ssh.close()
print("\n=== DONE ===")
