#!/usr/bin/env python3
"""Run remaining Supabase component import batches 008-012.
Splits each batch into individual INSERT statements and executes via Supabase REST.
Uses SUPABASE_SERVICE_ROLE_KEY or SUPABASE_URL + key from env.
"""
import os
import re
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("pip install supabase")
    raise

PROJECT_REF = "hnevnsxnhfibhbsipqvz"
BATCH_DIR = Path(__file__).resolve().parent

def get_supabase():
    url = os.environ.get("SUPABASE_URL") or f"https://{PROJECT_REF}.supabase.co"
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise SystemExit("Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
    return create_client(url, key)

def split_statements(content: str) -> list[str]:
    """Split SQL into individual INSERT statements (handle ON CONFLICT as part of same stmt)."""
    stmts = []
    current = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        current.append(line)
        if line.endswith(";"):
            stmts.append(" ".join(current))
            current = []
    if current:
        stmts.append(" ".join(current))
    return stmts

def main():
    sb = get_supabase()
    for i in range(8, 13):
        path = BATCH_DIR / f"_batch{i:03d}.sql"
        if not path.exists():
            print(f"Skip {path.name} (not found)")
            continue
        content = path.read_text()
        stmts = split_statements(content)
        print(f"{path.name}: {len(stmts)} statements")
        for j, sql in enumerate(stmts):
            try:
                sb.rpc("exec_sql", {"query": sql}).execute()
            except Exception as e:
                # Supabase Python doesn't expose raw SQL RPC by default; use postgrest
                try:
                    sb.postgrest.rpc("exec_sql", {"query": sql}).execute()
                except Exception:
                    print(f"  Statement {j+1} failed (RPC may not exist): {e}")
                    # Fallback: use REST insert - would need to parse VALUES
                    print("  Run statements manually via Supabase SQL Editor.")

if __name__ == "__main__":
    main()
