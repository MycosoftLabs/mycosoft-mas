-- Enable RLS Security Fixes - April 7, 2026
-- Resolves Supabase linter errors:
--   0007_policy_exists_rls_disabled: Tables with policies but RLS not enabled
--   0013_rls_disabled_in_public: Public tables without RLS
--   0023_sensitive_columns_exposed: myco_users.password exposed without RLS
--
-- All 16 affected tables get RLS enabled + service_role full access + authenticated read.
-- myco_users additionally gets column-level protection: the password column is
-- revoked from anon/authenticated and a secure view is provided.

BEGIN;

-- ============================================================================
-- 1. Enable RLS on every affected table
-- ============================================================================

ALTER TABLE IF EXISTS public.agent_incident_activity  ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_log_chain        ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_users                ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mushroom_discoveries      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_transactions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.lab_kit_requests          ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_leaderboard          ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_achievements         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_location_cache       ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_causality        ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_chain_details    ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cascade_predictions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.agent_resolutions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.agent_run_log             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.system_status             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mycobrain_data            ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. Service-role full access policies (idempotent — skip if exists)
-- ============================================================================

DO $$
DECLARE
  tbl text;
  pol text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'agent_incident_activity',
    'incident_log_chain',
    'myco_users',
    'mushroom_discoveries',
    'myco_transactions',
    'lab_kit_requests',
    'myco_leaderboard',
    'myco_achievements',
    'myco_location_cache',
    'incident_causality',
    'incident_chain_details',
    'cascade_predictions',
    'agent_resolutions',
    'agent_run_log',
    'system_status',
    'mycobrain_data'
  ] LOOP
    -- Service role: full access
    pol := 'Allow service role all ' || tbl;
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = tbl AND policyname = pol
    ) THEN
      EXECUTE format(
        'CREATE POLICY %I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)',
        pol, tbl
      );
    END IF;

    -- Authenticated: read access
    pol := 'Allow authenticated read ' || tbl;
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = tbl AND policyname = pol
    ) THEN
      EXECUTE format(
        'CREATE POLICY %I ON public.%I FOR SELECT TO authenticated USING (true)',
        pol, tbl
      );
    END IF;
  END LOOP;
END $$;

-- ============================================================================
-- 3. myco_users: protect the password column from API exposure
--    Revoke direct column access and provide a safe view.
-- ============================================================================

-- Revoke SELECT on the password column from public-facing roles
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'myco_users' AND column_name = 'password'
  ) THEN
    EXECUTE 'REVOKE SELECT (password) ON public.myco_users FROM anon, authenticated';
  END IF;
END $$;

-- Create a safe view that excludes the password column
CREATE OR REPLACE VIEW public.myco_users_safe AS
  SELECT *
  FROM public.myco_users;

-- The view above uses SELECT * but the column-level REVOKE means anon/authenticated
-- cannot read the password column through the table directly. For the view, we
-- explicitly drop the password column:
DROP VIEW IF EXISTS public.myco_users_safe;

DO $$
DECLARE
  cols text;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'myco_users'
  ) THEN
    SELECT string_agg(quote_ident(column_name), ', ')
    INTO cols
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'myco_users'
      AND column_name != 'password';

    IF cols IS NOT NULL THEN
      EXECUTE format('CREATE OR REPLACE VIEW public.myco_users_safe AS SELECT %s FROM public.myco_users', cols);
      EXECUTE 'GRANT SELECT ON public.myco_users_safe TO authenticated';
    END IF;
  END IF;
END $$;

-- ============================================================================
-- 4. Force-enable RLS for table owners too (prevents bypass by table owner)
-- ============================================================================

ALTER TABLE IF EXISTS public.agent_incident_activity  FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_log_chain        FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_users                FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mushroom_discoveries      FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_transactions         FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.lab_kit_requests          FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_leaderboard          FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_achievements         FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.myco_location_cache       FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_causality        FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.incident_chain_details    FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cascade_predictions       FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.agent_resolutions         FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.agent_run_log             FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.system_status             FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mycobrain_data            FORCE ROW LEVEL SECURITY;

COMMIT;
