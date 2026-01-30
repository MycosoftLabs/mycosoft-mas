-- Supabase RLS Fixes - January 29, 2026
-- Enable RLS and ensure service_role policies for flagged public tables.
-- NOTE: Existing policies (if any) remain in place.

DO $$
DECLARE
  table_name text;
  policy_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
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
    'agent_run_log'
  ] LOOP
    EXECUTE format('ALTER TABLE IF EXISTS public.%I ENABLE ROW LEVEL SECURITY', table_name);

    policy_name := 'service_role_all_' || table_name;
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = table_name
        AND policyname = policy_name
    ) THEN
      EXECUTE format(
        'CREATE POLICY %I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)',
        policy_name,
        table_name
      );
    END IF;
  END LOOP;
END $$;
