---
name: database-migration
description: Create and apply database migrations for the MINDEX PostgreSQL database. Use when modifying database schema, adding tables, or changing columns.
---

# Database Migrations

## MINDEX Database

All Mycosoft data is stored in MINDEX on VM 192.168.0.189.

Connection: `postgresql://mycosoft:mycosoft@192.168.0.189:5432/mindex`

## Steps

```
Migration Progress:
- [ ] Step 1: Create migration file
- [ ] Step 2: Review the SQL
- [ ] Step 3: Apply to MINDEX VM
- [ ] Step 4: Verify schema
```

### Step 1: Create migration file

Create a numbered migration in `migrations/`:

```sql
-- migrations/NNNN_description.sql
-- Migration: Brief description
-- Date: YYYY-MM-DD
-- Author: [name]

BEGIN;

CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name);

COMMIT;
```

### Step 2: Review the SQL

- Use `IF NOT EXISTS` for all CREATE statements
- Use `IF EXISTS` for all DROP statements
- Wrap in transaction (BEGIN/COMMIT)
- Include rollback comments

### Step 3: Apply to MINDEX VM

```bash
ssh mycosoft@192.168.0.189

# Apply migration
psql -U mycosoft -d mindex -f /path/to/migration.sql

# Or from local machine
psql "postgresql://mycosoft:mycosoft@192.168.0.189:5432/mindex" -f migrations/NNNN_description.sql
```

### Step 4: Verify

```bash
# Check table exists
psql -U mycosoft -d mindex -c "\dt new_table"

# Check columns
psql -U mycosoft -d mindex -c "\d new_table"
```

## Safety Rules

- ALWAYS backup before destructive migrations
- ALWAYS use `IF NOT EXISTS` / `IF EXISTS`
- ALWAYS wrap in transactions
- NEVER drop tables without explicit confirmation
- Test on dev/staging before production
- Include rollback SQL as comments in the migration file

## Backup Before Migration

```bash
ssh mycosoft@192.168.0.189
pg_dump -U mycosoft mindex > /tmp/mindex_backup_$(date +%Y%m%d).sql
```
