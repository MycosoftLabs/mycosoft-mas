# CREP — Agent API Key Scope Contract (Draft — May 02, 2026)

**Status:** Draft — schema not applied in production  
**Blocks:** `CREPDashboardClient` layer entitlements (see `docs/NATUREOS_SHELL_INTEGRATION_BACKLOG_MAY02_2026.md`)

## Goal

Thread **`scope`** (and optional **`layers`**) from MAS-issued agent keys into the CREP dashboard so map layers and tools respect least-privilege access.

## Proposed contract (MAS)

- **Table / store:** `agent_api_keys` (or extend existing device/agent credential store) with columns:
  - `key_id` (uuid), `key_hash`, `agent_id`, `expires_at`, `scopes` (text[] or jsonb), `created_at`
- **`scopes` values (examples):** `crep:read`, `crep:layer:aviation`, `crep:layer:maritime`, `crep:admin`
- **Validation:** MAS middleware or website server route validates key → attaches `AgentKeyContext` to request.

## Proposed contract (website)

- **Header:** `X-Mycosoft-Agent-Key` (or session-bound equivalent after OAuth exchange).
- **`CREPDashboardClient`:** reads allowed layers from context; hides/disables UI for out-of-scope layers.
- **No mock scopes:** If key missing or invalid, show **authenticated empty** or **upgrade** state — no hardcoded sample scopes.

## Next steps

1. Align with existing MAS `api_keys` / device registry if present (avoid duplicate tables).  
2. Add migration + MAS router for key introspection (`GET /api/agent-keys/self` or similar).  
3. Wire Next.js CREP data loaders to forward key scope.
