# MINDEX Genetics Endpoint Fix – Feb 10, 2026

## Summary

The MINDEX genetics API was returning 500 because of an `id` type mismatch between the database and the Pydantic models.

## Root Cause

- Migration `0012_genetics.sql` defines `bio.genetic_sequence.id` as `SERIAL PRIMARY KEY` (integer).
- The genetics router and unified search models used `id: UUID`, causing validation errors when returning results.

## Changes Made

### 1. `mindex_api/routers/genetics.py`

- `GeneticSequenceResponse.id`: `UUID` → `int`
- `get_genetic_sequence(sequence_id)`: `UUID` → `int`
- `delete_genetic_sequence(sequence_id)`: `UUID` → `int`
- Removed unused `from uuid import UUID`

### 2. `mindex_api/routers/unified_search.py`

- `GeneticsResult.id`: `UUID` → `int` (to match `bio.genetic_sequence.id`)

## Deployment

1. Commit and push MINDEX changes to GitHub:

   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex
   git add mindex_api/routers/genetics.py mindex_api/routers/unified_search.py
   git commit -m "fix: genetics id type int to match bio.genetic_sequence SERIAL"
   git push origin main
   ```

2. Deploy to MINDEX VM (192.168.0.189):

   ```powershell
   $env:VM_PASSWORD = "your-vm-password"
   python _deploy_mindex.py
   ```

   Or manually:

   ```bash
   ssh mycosoft@192.168.0.189
   cd /home/mycosoft/mindex
   git fetch origin
   git reset --hard origin/main
   docker-compose build --no-cache mindex-api
   docker-compose up -d mindex-api
   ```

3. Verify:

   ```bash
   curl -s -H "X-API-Key: YOUR_KEY" "http://192.168.0.189:8000/api/mindex/genetics?limit=5"
   ```

   Expect `200` with `{"data": [], "pagination": {...}}` if the table is empty.

## Website Integration

The unified search route in the website (`app/api/search/unified/route.ts`) maps genetics results as:

- `id: \`mindex-seq-${s.id}\`` – works with both int and UUID.
- Compounds and genetics both return empty arrays on error or when the table is empty.

## Related

- Migration: `migrations/0012_genetics.sql`
- Compounds fix: `bio.compound` table created via `0007_compounds.sql`
- API catalog: `docs/API_CATALOG_FEB04_2026.md`
