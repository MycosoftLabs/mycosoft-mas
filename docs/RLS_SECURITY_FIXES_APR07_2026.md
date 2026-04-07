# RLS Security Fixes — April 7, 2026

## Summary

Resolves 18 Supabase database linter errors across 3 categories:

| Lint Code | Issue | Count |
|-----------|-------|-------|
| `0007_policy_exists_rls_disabled` | Tables have RLS policies but RLS not enabled | 2 |
| `0013_rls_disabled_in_public` | Public tables without RLS | 16 |
| `0023_sensitive_columns_exposed` | `myco_users.password` exposed via API | 1 |

## Affected Tables (16)

| Table | Had Policies? | New in This Migration? |
|-------|--------------|----------------------|
| `agent_incident_activity` | Yes | No (was in 005, RLS not applied) |
| `incident_log_chain` | Yes | No (was in 005, RLS not applied) |
| `myco_users` | No | No (was in 005, RLS not applied) |
| `mushroom_discoveries` | No | No (was in 005, RLS not applied) |
| `myco_transactions` | No | No (was in 005, RLS not applied) |
| `lab_kit_requests` | No | No (was in 005, RLS not applied) |
| `myco_leaderboard` | No | No (was in 005, RLS not applied) |
| `myco_achievements` | No | No (was in 005, RLS not applied) |
| `myco_location_cache` | No | No (was in 005, RLS not applied) |
| `incident_causality` | No | No (was in 005, RLS not applied) |
| `incident_chain_details` | No | No (was in 005, RLS not applied) |
| `cascade_predictions` | No | No (was in 005, RLS not applied) |
| `agent_resolutions` | No | No (was in 005, RLS not applied) |
| `agent_run_log` | No | No (was in 005, RLS not applied) |
| `system_status` | No | **Yes** |
| `mycobrain_data` | No | **Yes** |

## Changes Applied

### 1. RLS Enabled + Forced
All 16 tables get `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.

### 2. Policies Created
- **`service_role`**: Full access (`ALL`) on every table
- **`authenticated`**: Read access (`SELECT`) on every table

### 3. `myco_users` Password Protection
- `REVOKE SELECT (password)` from `anon` and `authenticated` roles
- Created `public.myco_users_safe` view excluding the password column

## How to Apply

Run against the Supabase/PostgreSQL database on MINDEX (192.168.0.189:5432):

```bash
psql -h 192.168.0.189 -U postgres -d mycosoft -f migrations/029_enable_rls_security_fixes_APR07_2026.sql
```

## Verification

After applying, re-run the Supabase linter. All 18 errors should be resolved.
