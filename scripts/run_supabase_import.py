#!/usr/bin/env python3
"""Read supabase_inserts.sql and output batches for MCP execute.
Prints batches to stdout - run via: python scripts/run_supabase_import.py
Then paste each batch into mcp_supabase_execute_sql.
Alternative: use Supabase MCP directly with batched queries.
"""
from pathlib import Path

BATCH_SIZE = 25

def main():
    path = Path(__file__).parent.parent / "data/amazon_import/supabase_inserts.sql"
    content = path.read_text(encoding="utf-8")
    # Split on semicolon followed by newline and possible INSERT
    stmts = [s.strip() + ";" for s in content.split(";") if s.strip()]
    total = len(stmts)
    batches = []
    for i in range(0, total, BATCH_SIZE):
        batch = stmts[i : i + BATCH_SIZE]
        batches.append("\n".join(batch))
    # Write batch files for manual/semi-automated run
    out_dir = path.parent
    for i, b in enumerate(batches):
        out_path = out_dir / f"supabase_batch_{i+1:03d}.sql"
        out_path.write_text(b, encoding="utf-8")
    print(f"Wrote {len(batches)} batch files to {out_dir}")
    return batches

if __name__ == "__main__":
    main()
