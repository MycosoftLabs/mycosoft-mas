-- Agent100 activity + billing audit tables — MAY03_2026
-- Apply in Supabase SQL editor or via migration pipeline.
-- RLS: service role bypasses; authenticated users need policies if exposed from PostgREST directly.

-- ---------------------------------------------------------------------------
-- Agents registry (harness metadata; optional link to profiles.id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent100_agents (
  id                TEXT PRIMARY KEY,
  archetype         TEXT NOT NULL,
  framework         TEXT NOT NULL,
  profile_id        UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  tier_budget_cents INTEGER NOT NULL DEFAULT 20000,
  stripe_customer_id TEXT,
  status            TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'halted', 'completed', 'error')),
  meta              JSONB NOT NULL DEFAULT '{}',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent100_agents_status ON public.agent100_agents(status);
CREATE INDEX IF NOT EXISTS idx_agent100_agents_archetype ON public.agent100_agents(archetype);

-- ---------------------------------------------------------------------------
-- Worldview calls (one row per HTTP attempt)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent100_calls (
  id              BIGSERIAL PRIMARY KEY,
  agent_id        TEXT NOT NULL REFERENCES public.agent100_agents(id) ON DELETE CASCADE,
  archetype       TEXT NOT NULL,
  framework       TEXT NOT NULL,
  dataset_id      TEXT,
  mode            TEXT NOT NULL CHECK (mode IN ('singular', 'multi', 'grouped', 'all_bundle', 'health', 'snapshot', 'stream', 'tile')),
  request_path    TEXT NOT NULL,
  status_code     INTEGER,
  latency_ms      INTEGER,
  cache           TEXT,
  cost_debited   INTEGER,
  rate_weight     INTEGER,
  bytes           INTEGER,
  schema_valid    BOOLEAN,
  freshness_ok    BOOLEAN,
  error_class     TEXT,
  request_id      TEXT,
  envelope_ok     BOOLEAN,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent100_calls_agent ON public.agent100_calls(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent100_calls_created ON public.agent100_calls(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent100_calls_dataset ON public.agent100_calls(dataset_id);

-- ---------------------------------------------------------------------------
-- Stripe / crypto charges (idempotent audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent100_charges (
  id               BIGSERIAL PRIMARY KEY,
  agent_id         TEXT NOT NULL REFERENCES public.agent100_agents(id) ON DELETE CASCADE,
  idempotency_key  TEXT NOT NULL UNIQUE,
  method           TEXT NOT NULL CHECK (method IN ('stripe', 'btc', 'usdc', 'sol', 'base', 'eth', 'internal_transfer')),
  amount_cents     INTEGER NOT NULL,
  currency         TEXT NOT NULL DEFAULT 'usd',
  stripe_invoice_id TEXT,
  tx_hash          TEXT,
  network          TEXT,
  status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'succeeded', 'failed', 'reversed')),
  raw              JSONB DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent100_charges_agent ON public.agent100_charges(agent_id);

-- ---------------------------------------------------------------------------
-- Structured agent feedback (critic / improver / advocate / documenter)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent100_feedback (
  id          BIGSERIAL PRIMARY KEY,
  agent_id    TEXT NOT NULL REFERENCES public.agent100_agents(id) ON DELETE CASCADE,
  archetype   TEXT NOT NULL,
  category    TEXT NOT NULL,
  severity    TEXT CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
  title       TEXT NOT NULL,
  body        TEXT NOT NULL,
  meta        JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent100_feedback_archetype ON public.agent100_feedback(archetype);

-- ---------------------------------------------------------------------------
-- Supervisor events (spawn, halt, cap_breach, wave)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent100_events (
  id         BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  agent_id   TEXT,
  payload    JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent100_events_type ON public.agent100_events(event_type);

COMMENT ON TABLE public.agent100_agents IS 'Agent100 harness — 100 internal paying customer personas';
COMMENT ON TABLE public.agent100_calls IS 'Per-request Worldview telemetry from harness';
COMMENT ON TABLE public.agent100_charges IS 'Stripe/crypto idempotent charge audit';
COMMENT ON TABLE public.agent100_feedback IS 'Agent-generated structured feedback for whitepaper';
COMMENT ON TABLE public.agent100_events IS 'Supervisor lifecycle events';
