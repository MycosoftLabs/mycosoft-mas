#!/usr/bin/env python3
"""
Seed soc_ops.compliance_controls from a Claude/Perplexity posture JSON file.

Expected JSON shape (one file drop-in):
{
  "provenance": {
    "source": "claude_catalog_jul10|perplexity_ssp|...",
    "note": "..."
  },
  "controls": [
    {
      "control_id": "3.1.1",
      "framework": "NIST_800_171",
      "family": "AC",
      "title": "Limit system access...",
      "implementation_state": "implemented|partial|planned|not_applicable|unknown",
      "evidence_uri": null,
      "state_snapshot": {"summary": "...", "notes": "...", "poam": false}
    }
  ]
}

Also accepts Claude website export where status is UI enum
(compliant/partial/non_compliant/not_applicable) — mapped to implementation_state.

Usage (from MAS repo, with MINDEX_DATABASE_URL or via SSH apply helper):
  python scripts/seed_soc_compliance_controls_jul10_2026.py data/compliance/posture.json
  python scripts/seed_soc_compliance_controls_jul10_2026.py --generate-provisional
  python scripts/seed_soc_compliance_controls_jul10_2026.py --apply-remote data/compliance/posture.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
DATA_DIR = ROOT / "data" / "compliance"
DEFAULT_OUT = DATA_DIR / "nist_800_171_cmmc_l2_posture_provisional_jul10_2026.json"

# Public NIST SP 800-171 Rev 2 control catalog (IDs + short titles). Not sensitive.
# Statuses in --generate-provisional follow the sprint target: 109 implemented,
# AU 3.3.4 planned (POA&M close 2026-11-09). Perplexity/Claude may overwrite.
# Tuple: (control_id, family, title)
NIST_171_CATALOG: List[tuple[str, str, str]] = [
    # 3.1 Access Control (22)
    ("3.1.1", "AC", "Limit system access to authorized users, processes, and devices"),
    ("3.1.2", "AC", "Limit system access to types of transactions and functions authorized"),
    ("3.1.3", "AC", "Control CUI flow in accordance with approved authorizations"),
    ("3.1.4", "AC", "Separate duties of individuals to reduce risk of malevolent activity"),
    ("3.1.5", "AC", "Employ least privilege principle including privileged accounts"),
    ("3.1.6", "AC", "Use non-privileged accounts when accessing nonsecurity functions"),
    ("3.1.7", "AC", "Prevent non-privileged users from executing privileged functions"),
    ("3.1.8", "AC", "Limit unsuccessful logon attempts"),
    ("3.1.9", "AC", "Provide privacy and security notices consistent with applicable CUI rules"),
    ("3.1.10", "AC", "Use session lock with pattern-hiding displays"),
    ("3.1.11", "AC", "Terminate user sessions after defined conditions"),
    ("3.1.12", "AC", "Monitor and control remote access sessions"),
    ("3.1.13", "AC", "Employ cryptographic mechanisms for remote access sessions"),
    ("3.1.14", "AC", "Route remote access through managed access control points"),
    ("3.1.15", "AC", "Authorize remote execution of privileged commands"),
    ("3.1.16", "AC", "Authorize wireless access prior to allowing connections"),
    ("3.1.17", "AC", "Protect wireless access using authentication and encryption"),
    ("3.1.18", "AC", "Control connection of mobile devices"),
    ("3.1.19", "AC", "Encrypt CUI on mobile devices and mobile computing platforms"),
    ("3.1.20", "AC", "Verify and control connections to external systems"),
    ("3.1.21", "AC", "Limit use of portable storage devices on external systems"),
    ("3.1.22", "AC", "Control CUI posted or processed on publicly accessible systems"),
    # 3.2 Awareness and Training (3)
    ("3.2.1", "AT", "Ensure managers, systems administrators, and users are aware of security risks"),
    ("3.2.2", "AT", "Ensure personnel are trained to carry out assigned information security duties"),
    ("3.2.3", "AT", "Provide security awareness training on recognizing and reporting insider threats"),
    # 3.3 Audit and Accountability (9)
    ("3.3.1", "AU", "Create and retain system audit logs to enable monitoring and investigation"),
    ("3.3.2", "AU", "Ensure actions of individual system users can be uniquely traced"),
    ("3.3.3", "AU", "Review and update logged events"),
    ("3.3.4", "AU", "Alert in the event of an audit logging process failure"),
    ("3.3.5", "AU", "Correlate audit record review, analysis, and reporting processes"),
    ("3.3.6", "AU", "Provide audit record reduction and report generation"),
    ("3.3.7", "AU", "Provide a system capability that compares and synchronizes internal clocks"),
    ("3.3.8", "AU", "Protect audit information and audit logging tools from unauthorized access"),
    ("3.3.9", "AU", "Limit management of audit logging functionality to privileged users"),
    # 3.4 Configuration Management (9)
    ("3.4.1", "CM", "Establish and maintain baseline configurations and inventories"),
    ("3.4.2", "CM", "Establish and enforce security configuration settings"),
    ("3.4.3", "CM", "Track, review, approve/disapprove, and log changes to systems"),
    ("3.4.4", "CM", "Analyze security impact of changes prior to implementation"),
    ("3.4.5", "CM", "Define, document, approve, and enforce physical and logical access restrictions"),
    ("3.4.6", "CM", "Employ least functionality principle"),
    ("3.4.7", "CM", "Restrict, disable, or prevent use of nonessential programs, functions, ports"),
    ("3.4.8", "CM", "Apply deny-by-exception (blacklisting) policy to prevent unauthorized software"),
    ("3.4.9", "CM", "Control and monitor user-installed software"),
    # 3.5 Identification and Authentication (11)
    ("3.5.1", "IA", "Identify system users, processes acting on behalf of users, and devices"),
    ("3.5.2", "IA", "Authenticate identities of users, processes, or devices before access"),
    ("3.5.3", "IA", "Use multifactor authentication for local and network access"),
    ("3.5.4", "IA", "Employ replay-resistant authentication mechanisms"),
    ("3.5.5", "IA", "Prevent reuse of identifiers for a defined period"),
    ("3.5.6", "IA", "Disable identifiers after a defined period of inactivity"),
    ("3.5.7", "IA", "Enforce minimum password complexity and change of characters"),
    ("3.5.8", "IA", "Prohibit password reuse for a specified number of generations"),
    ("3.5.9", "IA", "Allow temporary password use for system logons with immediate change"),
    ("3.5.10", "IA", "Store and transmit only cryptographically-protected passwords"),
    ("3.5.11", "IA", "Obscure feedback of authentication information"),
    # 3.6 Incident Response (3)
    ("3.6.1", "IR", "Establish operational incident-handling capability"),
    ("3.6.2", "IR", "Track, document, and report incidents to designated officials"),
    ("3.6.3", "IR", "Test the organizational incident response capability"),
    # 3.7 Maintenance (6)
    ("3.7.1", "MA", "Perform maintenance on organizational systems"),
    ("3.7.2", "MA", "Provide controls on tools, techniques, mechanisms, and personnel"),
    ("3.7.3", "MA", "Ensure equipment removed for off-site maintenance is sanitized"),
    ("3.7.4", "MA", "Check media containing diagnostic tools for malicious code"),
    ("3.7.5", "MA", "Require multifactor authentication to establish nonlocal maintenance sessions"),
    ("3.7.6", "MA", "Supervise maintenance activities of maintenance personnel"),
    # 3.8 Media Protection (9)
    ("3.8.1", "MP", "Protect system media containing CUI"),
    ("3.8.2", "MP", "Limit access to CUI on system media to authorized users"),
    ("3.8.3", "MP", "Sanitize or destroy system media containing CUI before disposal"),
    ("3.8.4", "MP", "Mark media with necessary CUI markings"),
    ("3.8.5", "MP", "Control access to media containing CUI and maintain accountability"),
    ("3.8.6", "MP", "Implement cryptographic mechanisms to protect CUI on digital media"),
    ("3.8.7", "MP", "Control use of removable media on system components"),
    ("3.8.8", "MP", "Prohibit use of portable storage devices when no identifiable owner"),
    ("3.8.9", "MP", "Protect confidentiality of backup CUI at storage locations"),
    # 3.9 Personnel Security (2)
    ("3.9.1", "PS", "Screen individuals prior to authorizing access to systems containing CUI"),
    ("3.9.2", "PS", "Ensure CUI and systems are protected during personnel actions"),
    # 3.10 Physical Protection (6)
    ("3.10.1", "PE", "Limit physical access to systems, equipment, and operating environments"),
    ("3.10.2", "PE", "Protect and monitor physical facility and support infrastructure"),
    ("3.10.3", "PE", "Escort visitors and monitor visitor activity"),
    ("3.10.4", "PE", "Maintain audit logs of physical access"),
    ("3.10.5", "PE", "Control and manage physical access devices"),
    ("3.10.6", "PE", "Enforce safeguarding measures for CUI at alternate work sites"),
    # 3.11 Risk Assessment (3)
    ("3.11.1", "RA", "Periodically assess risk to organizational operations and assets"),
    ("3.11.2", "RA", "Scan for vulnerabilities and remediate"),
    ("3.11.3", "RA", "Remediate vulnerabilities in accordance with risk assessments"),
    # 3.12 Security Assessment (4)
    ("3.12.1", "CA", "Periodically assess security controls"),
    ("3.12.2", "CA", "Develop and implement plans of action designed to correct deficiencies"),
    ("3.12.3", "CA", "Monitor security controls on an ongoing basis"),
    ("3.12.4", "CA", "Develop, document, and periodically update system security plans"),
    # 3.13 System and Communications Protection (16)
    ("3.13.1", "SC", "Monitor, control, and protect communications at external boundaries"),
    ("3.13.2", "SC", "Employ architectural designs and techniques that promote effective security"),
    ("3.13.3", "SC", "Separate user functionality from system management functionality"),
    ("3.13.4", "SC", "Prevent unauthorized transfer of information via shared resources"),
    ("3.13.5", "SC", "Implement subnetworks for publicly accessible system components"),
    ("3.13.6", "SC", "Deny network communications traffic by default"),
    ("3.13.7", "SC", "Prevent remote devices from simultaneously establishing non-remote connections"),
    ("3.13.8", "SC", "Implement cryptographic mechanisms to prevent unauthorized disclosure"),
    ("3.13.9", "SC", "Terminate network connections associated with communications sessions"),
    ("3.13.10", "SC", "Establish and manage cryptographic keys"),
    ("3.13.11", "SC", "Employ FIPS-validated cryptography when used to protect CUI"),
    ("3.13.12", "SC", "Prohibit remote activation of collaborative computing devices"),
    ("3.13.13", "SC", "Control and monitor use of mobile code"),
    ("3.13.14", "SC", "Control and monitor use of Voice over Internet Protocol (VoIP)"),
    ("3.13.15", "SC", "Protect authenticity of communications sessions"),
    ("3.13.16", "SC", "Protect confidentiality of CUI at rest"),
    # 3.14 System and Information Integrity (7)
    ("3.14.1", "SI", "Identify, report, and correct system flaws in a timely manner"),
    ("3.14.2", "SI", "Provide protection from malicious code at designated locations"),
    ("3.14.3", "SI", "Monitor system security alerts and take action"),
    ("3.14.4", "SI", "Update malicious code protection mechanisms when new releases available"),
    ("3.14.5", "SI", "Perform periodic scans and real-time scans of files from external sources"),
    ("3.14.6", "SI", "Monitor organizational systems including inbound and outbound communications"),
    ("3.14.7", "SI", "Identify unauthorized use of organizational systems"),
]

FAMILY_TO_CMMC = {
    "AC": "AC",
    "AT": "AT",
    "AU": "AU",
    "CM": "CM",
    "IA": "IA",
    "IR": "IR",
    "MA": "MA",
    "MP": "MP",
    "PS": "PS",
    "PE": "PE",
    "RA": "RA",
    "CA": "CA",
    "SC": "SC",
    "SI": "SI",
}

UI_STATUS_TO_IMPL = {
    "compliant": "implemented",
    "partial": "partial",
    "non_compliant": "planned",
    "not_applicable": "not_applicable",
    "implemented": "implemented",
    "planned": "planned",
    "unknown": "unknown",
}


def load_creds() -> None:
    if not CREDS.exists():
        return
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def generate_provisional() -> Dict[str, Any]:
    if len(NIST_171_CATALOG) != 110:
        raise SystemExit(f"Catalog size {len(NIST_171_CATALOG)} != 110")
    controls: List[Dict[str, Any]] = []
    for control_id, family, title in NIST_171_CATALOG:
        state = "planned" if control_id == "3.3.4" else "implemented"
        snap: Dict[str, Any] = {
            "summary": title,
            "provenance": "provisional_sprint_target_jul10_2026",
        }
        if control_id == "3.3.4":
            snap.update(
                {
                    "notes": "On POA&M — audit logging process failure alerting",
                    "poam": True,
                    "poam_close": "2026-11-09",
                }
            )
        controls.append(
            {
                "control_id": control_id,
                "framework": "NIST_800_171",
                "family": family,
                "title": title,
                "implementation_state": state,
                "evidence_uri": None,
                "state_snapshot": snap,
            }
        )
        # CMMC L2 practice IDs mirror NIST 171 requirements
        cmmc_id = f"{FAMILY_TO_CMMC[family]}.L2-{control_id}"
        controls.append(
            {
                "control_id": cmmc_id,
                "framework": "CMMC_L2",
                "family": family,
                "title": title,
                "implementation_state": state,
                "evidence_uri": None,
                "state_snapshot": {**snap, "nist_800_171": control_id},
            }
        )
    return {
        "provenance": {
            "source": "mas_provisional_catalog_jul10_2026",
            "catalog": "NIST SP 800-171 Rev 2 public control list (110)",
            "posture": "109 implemented / 1 planned (3.3.4 POA&M close 2026-11-09)",
            "note": (
                "Statuses are the sprint target overlay pending Perplexity SSP confirmation. "
                "Claude website catalog/posture file should replace this when available."
            ),
        },
        "controls": controls,
    }


def normalize_controls(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("controls") or []
    out: List[Dict[str, Any]] = []
    for raw in rows:
        control_id = str(raw.get("control_id") or raw.get("id") or "").strip()
        if not control_id:
            continue
        framework = str(raw.get("framework") or "NIST_800_171").replace("-", "_").replace(" ", "_")
        if framework.upper().startswith("NIST") and "171" in framework:
            framework = "NIST_800_171"
        elif "CMMC" in framework.upper() and "L2" in framework.upper():
            framework = "CMMC_L2"
        impl = raw.get("implementation_state")
        if not impl and raw.get("status"):
            impl = UI_STATUS_TO_IMPL.get(str(raw["status"]), "unknown")
        impl = str(impl or "unknown")
        snap = raw.get("state_snapshot")
        if not isinstance(snap, dict):
            snap = {}
            if raw.get("description"):
                snap["summary"] = raw["description"]
            if raw.get("notes"):
                snap["notes"] = raw["notes"]
        out.append(
            {
                "control_id": control_id,
                "framework": framework,
                "family": raw.get("family"),
                "title": raw.get("title") or raw.get("name") or control_id,
                "implementation_state": impl,
                "evidence_uri": raw.get("evidence_uri"),
                "state_snapshot": snap,
            }
        )
    return out


async def upsert_local(controls: List[Dict[str, Any]], database_url: str) -> int:
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        n = 0
        for row in controls:
            await conn.execute(
                """
                INSERT INTO soc_ops.compliance_controls
                    (control_id, framework, family, title, implementation_state, evidence_uri,
                     last_verified_at, state_snapshot, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7::jsonb, NOW())
                ON CONFLICT (control_id) DO UPDATE SET
                    framework = EXCLUDED.framework,
                    family = COALESCE(EXCLUDED.family, soc_ops.compliance_controls.family),
                    title = COALESCE(EXCLUDED.title, soc_ops.compliance_controls.title),
                    implementation_state = EXCLUDED.implementation_state,
                    evidence_uri = COALESCE(EXCLUDED.evidence_uri, soc_ops.compliance_controls.evidence_uri),
                    last_verified_at = NOW(),
                    state_snapshot = EXCLUDED.state_snapshot,
                    updated_at = NOW()
                """,
                row["control_id"],
                row["framework"],
                row.get("family"),
                row.get("title"),
                row["implementation_state"],
                row.get("evidence_uri"),
                json.dumps(row.get("state_snapshot") or {}),
            )
            n += 1
        return n
    finally:
        await conn.close()


def apply_remote(controls: List[Dict[str, Any]]) -> int:
    import paramiko

    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    host = os.environ.get("MAS_HOST", "192.168.0.188")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=password, timeout=30)
    sftp = ssh.open_sftp()
    remote_json = "/tmp/compliance_seed_jul10.json"
    with sftp.file(remote_json, "w") as f:
        f.write(json.dumps({"controls": controls}))
    remote_py = r'''
import asyncio, json, os
from pathlib import Path

def db_url():
    url = ""
    for line in Path("/home/mycosoft/mycosoft/mas/.env").read_text(errors="replace").splitlines():
        if line.startswith("MINDEX_DATABASE_URL="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
        if line.startswith("DATABASE_URL=") and not url:
            url = line.split("=",1)[1].strip().strip('"').strip("'")
    if url:
        return url
    raise SystemExit("no db url")

async def main():
    import asyncpg
    payload = json.loads(Path("/tmp/compliance_seed_jul10.json").read_text())
    rows = payload["controls"]
    conn = await asyncpg.connect(db_url())
    n = 0
    try:
        for row in rows:
            await conn.execute(
                """
                INSERT INTO soc_ops.compliance_controls
                    (control_id, framework, family, title, implementation_state, evidence_uri,
                     last_verified_at, state_snapshot, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7::jsonb,NOW())
                ON CONFLICT (control_id) DO UPDATE SET
                    framework = EXCLUDED.framework,
                    family = COALESCE(EXCLUDED.family, soc_ops.compliance_controls.family),
                    title = COALESCE(EXCLUDED.title, soc_ops.compliance_controls.title),
                    implementation_state = EXCLUDED.implementation_state,
                    evidence_uri = COALESCE(EXCLUDED.evidence_uri, soc_ops.compliance_controls.evidence_uri),
                    last_verified_at = NOW(),
                    state_snapshot = EXCLUDED.state_snapshot,
                    updated_at = NOW()
                """,
                row["control_id"], row["framework"], row.get("family"), row.get("title"),
                row["implementation_state"], row.get("evidence_uri"),
                json.dumps(row.get("state_snapshot") or {}),
            )
            n += 1
        total = await conn.fetchval("SELECT COUNT(*) FROM soc_ops.compliance_controls")
        impl = await conn.fetchval(
            "SELECT COUNT(*) FROM soc_ops.compliance_controls WHERE implementation_state='implemented'"
        )
        print(f"UPSERTED={n} TOTAL={total} IMPLEMENTED={impl}")
    finally:
        await conn.close()

asyncio.run(main())
'''
    with sftp.file("/tmp/seed_compliance.py", "w") as f:
        f.write(remote_py)
    sftp.close()
    py = "/home/mycosoft/mycosoft/mas/venv/bin/python"
    _i, o, e = ssh.exec_command(f"{py} /tmp/seed_compliance.py", timeout=300)
    out = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    code = o.channel.recv_exit_status()
    print(out)
    if err.strip():
        print(err[:500], file=sys.stderr)
    ssh.close()
    if code != 0:
        raise SystemExit(code)
    return len(controls)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", nargs="?", help="Posture JSON from Claude/Perplexity")
    parser.add_argument("--generate-provisional", action="store_true")
    parser.add_argument("--apply-remote", action="store_true", help="Seed via SSH to MAS→MINDEX")
    parser.add_argument("--database-url", default=os.environ.get("MINDEX_DATABASE_URL", ""))
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.generate_provisional:
        payload = generate_provisional()
        DEFAULT_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {DEFAULT_OUT} controls={len(payload['controls'])}")
        path = DEFAULT_OUT
    elif args.json_path:
        path = Path(args.json_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        parser.error("Provide json_path or --generate-provisional")
        return 2

    controls = normalize_controls(payload if "controls" in payload else {"controls": payload})
    print(f"Normalized controls: {len(controls)}")

    if args.apply_remote or (args.generate_provisional and not args.database_url):
        apply_remote(controls)
        return 0

    if not args.database_url:
        print("No --database-url; wrote/normalized only. Use --apply-remote to seed MAS DB.")
        return 0

    n = asyncio.run(upsert_local(controls, args.database_url))
    print(f"Upserted locally: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
