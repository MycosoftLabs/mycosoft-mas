#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM VERIFICATION SCRIPT
Verifies both Sandbox VM and MAS VM are working and all services are communicating
"""

import paramiko
import requests
import json
import sys
from datetime import datetime

# Configuration
SANDBOX_VM_IP = "192.168.0.187"
MAS_VM_IP = "192.168.0.187"  # Same VM hosts both for now
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"
SANDBOX_URL = "https://sandbox.mycosoft.com"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "•", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "HEAD": "▶"}
    print(f"[{ts}] {icons.get(level, '•')} {msg}")

def run_ssh_cmd(ssh, cmd, timeout=30):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return out, err
    except Exception as e:
        return None, str(e)

def check_url(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout, verify=False)
        return resp.status_code, resp.text[:500] if resp.text else ""
    except Exception as e:
        return None, str(e)

def check_api_json(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("\n" + "="*70)
    print("     MYCOSOFT COMPREHENSIVE SYSTEM VERIFICATION")
    print("     Sandbox VM + MAS VM + All Services")
    print("="*70 + "\n")
    
    results = {
        "sandbox_vm": {},
        "containers": {},
        "mindex_api": {},
        "website": {},
        "external_endpoints": {},
        "databases": {},
        "integrations": {}
    }
    
    # =====================================================
    # SECTION 1: SSH to Sandbox VM and check containers
    # =====================================================
    print("-"*70)
    print("  SECTION 1: Sandbox VM Status (192.168.0.187)")
    print("-"*70)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SANDBOX_VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
        log("Connected to Sandbox VM", "OK")
        results["sandbox_vm"]["connected"] = True
        
        # Check uptime
        out, _ = run_ssh_cmd(ssh, "uptime")
        log(f"VM Uptime: {out}")
        results["sandbox_vm"]["uptime"] = out
        
        # Check all Docker containers
        log("Checking Docker containers...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'")
        containers = []
        if out:
            for line in out.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    name = parts[0] if len(parts) > 0 else ""
                    status = parts[1] if len(parts) > 1 else ""
                    ports = parts[2] if len(parts) > 2 else ""
                    containers.append({"name": name, "status": status, "ports": ports})
                    status_icon = "OK" if "Up" in status else "WARN"
                    log(f"  {name}: {status}", status_icon)
        results["containers"]["list"] = containers
        
        # Check MINDEX-specific containers
        log("Checking MINDEX services...", "HEAD")
        mindex_containers = ["mindex-postgres-data", "mindex-api", "mindex-etl-scheduler"]
        for mc in mindex_containers:
            out, _ = run_ssh_cmd(ssh, f"docker ps --filter name={mc} --format '{{{{.Status}}}}'")
            is_running = "Up" in (out or "")
            results["containers"][mc] = is_running
            log(f"  {mc}: {'Running' if is_running else 'NOT RUNNING'}", "OK" if is_running else "ERROR")
        
        # Check MINDEX API health
        log("Testing MINDEX API endpoints...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s http://localhost:8000/api/mindex/health")
        try:
            health = json.loads(out) if out else {}
            results["mindex_api"]["health"] = health
            is_healthy = health.get("status") == "healthy" or health.get("database") == True
            log(f"  Health: {out}", "OK" if is_healthy else "WARN")
        except:
            results["mindex_api"]["health"] = {"error": out}
            log(f"  Health: {out}", "WARN")
        
        # Check MINDEX API stats
        out, _ = run_ssh_cmd(ssh, "curl -s http://localhost:8000/api/mindex/stats")
        try:
            stats = json.loads(out) if out else {}
            results["mindex_api"]["stats"] = stats
            total_taxa = stats.get("total_taxa", 0)
            total_obs = stats.get("total_observations", 0)
            log(f"  Stats: {total_taxa} taxa, {total_obs} observations", "OK" if total_taxa > 0 else "WARN")
        except:
            results["mindex_api"]["stats"] = {"error": out}
            log(f"  Stats: {out}", "WARN")
        
        # Check PostgreSQL
        log("Testing PostgreSQL connection...", "HEAD")
        out, err = run_ssh_cmd(ssh, "docker exec mindex-postgres-data psql -U mindex -d mindex -c 'SELECT COUNT(*) FROM taxa;' -t")
        try:
            taxa_count = int(out.strip()) if out else 0
            results["databases"]["postgres_taxa_count"] = taxa_count
            log(f"  PostgreSQL Taxa Count: {taxa_count}", "OK" if taxa_count > 0 else "WARN")
        except:
            results["databases"]["postgres_error"] = err or out
            log(f"  PostgreSQL: {err or out}", "WARN")
        
        # Check ETL scheduler logs
        log("Checking ETL scheduler status...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker logs mindex-etl-scheduler --tail 5 2>&1")
        results["containers"]["etl_logs"] = out
        log(f"  ETL Scheduler logs:\n    " + (out.replace("\n", "\n    ") if out else "No logs"))
        
        # Check website container
        log("Testing Website container...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        website_status = out.strip() if out else "000"
        results["website"]["local_http"] = website_status
        log(f"  Local HTTP Status: {website_status}", "OK" if website_status == "200" else "ERROR")
        
        # Check NAS mount
        log("Checking NAS mount...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "ls -la /opt/mycosoft/media 2>&1 | head -5")
        results["sandbox_vm"]["nas_mount"] = out
        log(f"  NAS Mount:\n    " + (out.replace("\n", "\n    ") if out else "Not accessible"))
        
        ssh.close()
        
    except Exception as e:
        log(f"Failed to connect to Sandbox VM: {e}", "ERROR")
        results["sandbox_vm"]["error"] = str(e)
    
    # =====================================================
    # SECTION 2: External Endpoint Tests (from this machine)
    # =====================================================
    print("\n" + "-"*70)
    print("  SECTION 2: External Endpoint Tests")
    print("-"*70)
    
    endpoints = [
        ("Sandbox Homepage", f"{SANDBOX_URL}/"),
        ("MINDEX Dashboard", f"{SANDBOX_URL}/natureos/mindex"),
        ("MINDEX API Stats", f"{SANDBOX_URL}/api/natureos/mindex/stats"),
        ("MINDEX API Health", f"{SANDBOX_URL}/api/natureos/mindex/health"),
        ("Ancestry Page", f"{SANDBOX_URL}/ancestry"),
        ("Security Incidents", f"{SANDBOX_URL}/security/incidents"),
        ("API Health", f"{SANDBOX_URL}/api/health"),
        ("Earth Sim", f"{SANDBOX_URL}/natureos/earth-sim"),
    ]
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    for name, url in endpoints:
        status, content = check_url(url)
        results["external_endpoints"][name] = {"status": status, "url": url}
        if status == 200:
            log(f"{name}: HTTP {status}", "OK")
        elif status:
            log(f"{name}: HTTP {status}", "WARN")
        else:
            log(f"{name}: FAILED - {content[:100]}", "ERROR")
    
    # Check MINDEX Stats in detail
    log("Fetching detailed MINDEX stats...", "HEAD")
    stats_data = check_api_json(f"{SANDBOX_URL}/api/natureos/mindex/stats")
    if "error" not in stats_data:
        log(f"  Data Source: {stats_data.get('data_source', 'unknown')}")
        log(f"  Total Taxa: {stats_data.get('total_taxa', 0)}")
        log(f"  Total Observations: {stats_data.get('total_observations', 0)}")
        log(f"  Observations w/Location: {stats_data.get('observations_with_location', 0)}")
        log(f"  ETL Status: {stats_data.get('etl_status', 'unknown')}")
        log(f"  Taxa by Source: {stats_data.get('taxa_by_source', {})}")
        results["mindex_api"]["external_stats"] = stats_data
    else:
        log(f"  Error: {stats_data.get('error')}", "WARN")
    
    # =====================================================
    # SECTION 3: Integration Tests
    # =====================================================
    print("\n" + "-"*70)
    print("  SECTION 3: Integration Tests")
    print("-"*70)
    
    # Test CREP integration
    log("Testing CREP integration...", "HEAD")
    crep_status, _ = check_url(f"{SANDBOX_URL}/crep")
    results["integrations"]["crep"] = crep_status == 200
    log(f"  CREP: {'Available' if crep_status == 200 else 'Not available'}", "OK" if crep_status == 200 else "WARN")
    
    # Test NatureOS integration
    log("Testing NatureOS integration...", "HEAD")
    natureos_status, _ = check_url(f"{SANDBOX_URL}/natureos")
    results["integrations"]["natureos"] = natureos_status == 200
    log(f"  NatureOS: {'Available' if natureos_status == 200 else 'Not available'}", "OK" if natureos_status == 200 else "WARN")
    
    # Test Ledger status
    log("Testing Ledger integrations...", "HEAD")
    ledger_data = check_api_json(f"{SANDBOX_URL}/api/natureos/mindex/ledger")
    if "error" not in ledger_data:
        for chain in ["hypergraph", "solana", "bitcoin"]:
            if chain in ledger_data:
                connected = ledger_data[chain].get("connected", False)
                log(f"  {chain.capitalize()}: {'Connected' if connected else 'Not connected'}", "OK" if connected else "WARN")
        results["integrations"]["ledger"] = ledger_data
    else:
        log(f"  Ledger Error: {ledger_data.get('error')}", "WARN")
    
    # =====================================================
    # SECTION 4: Database Route Tests
    # =====================================================
    print("\n" + "-"*70)
    print("  SECTION 4: Database Route Tests")
    print("-"*70)
    
    db_routes = [
        ("Taxa List", f"{SANDBOX_URL}/api/natureos/mindex/taxa?limit=5"),
        ("Observations", f"{SANDBOX_URL}/api/natureos/mindex/observations?limit=5"),
        ("Search", f"{SANDBOX_URL}/api/search?q=Amanita&limit=5"),
    ]
    
    for name, url in db_routes:
        data = check_api_json(url)
        if "error" not in data:
            if isinstance(data, list):
                log(f"{name}: {len(data)} items returned", "OK")
            elif isinstance(data, dict):
                total = data.get("total", data.get("count", len(data.get("data", []))))
                log(f"{name}: {total} total items", "OK")
            results["integrations"][name.lower().replace(" ", "_")] = True
        else:
            log(f"{name}: {data.get('error')}", "WARN")
            results["integrations"][name.lower().replace(" ", "_")] = False
    
    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "="*70)
    print("     VERIFICATION SUMMARY")
    print("="*70)
    
    all_ok = True
    summary_items = []
    
    # VM Status
    if results["sandbox_vm"].get("connected"):
        summary_items.append(("Sandbox VM Connection", True))
    else:
        summary_items.append(("Sandbox VM Connection", False))
        all_ok = False
    
    # Container Status
    for mc in ["mindex-postgres-data", "mindex-api", "mindex-etl-scheduler"]:
        is_running = results["containers"].get(mc, False)
        summary_items.append((f"Container: {mc}", is_running))
        if not is_running:
            all_ok = False
    
    # Website
    website_ok = results.get("website", {}).get("local_http") == "200"
    summary_items.append(("Website Container", website_ok))
    if not website_ok:
        all_ok = False
    
    # MINDEX API
    api_stats = results.get("mindex_api", {}).get("stats", {})
    has_taxa = api_stats.get("total_taxa", 0) > 0
    summary_items.append(("MINDEX API (Taxa)", has_taxa))
    if not has_taxa:
        all_ok = False
    
    # External endpoints
    for name, info in results.get("external_endpoints", {}).items():
        is_ok = info.get("status") == 200
        summary_items.append((f"Endpoint: {name}", is_ok))
    
    print()
    for item, status in summary_items:
        icon = "✓" if status else "✗"
        color_code = "OK" if status else "ERROR"
        log(f"{item}: {'PASS' if status else 'FAIL'}", color_code)
    
    print("\n" + "-"*70)
    if all_ok:
        print("  ✓ ALL SYSTEMS OPERATIONAL")
    else:
        print("  ⚠ SOME SYSTEMS NEED ATTENTION")
    print("-"*70 + "\n")
    
    # Save results to file
    with open("system_verification_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    log("Results saved to system_verification_results.json")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
