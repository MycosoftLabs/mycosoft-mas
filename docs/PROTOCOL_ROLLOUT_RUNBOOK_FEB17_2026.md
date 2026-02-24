# Protocol Rollout Runbook – February 17, 2026

Operational runbook for A2A, WebMCP, and UCP protocol-layer rollout across MAS, Website, and MINDEX. Staged enablement and observability.

## Feature flags

| Env var | Default | Scope | Purpose |
|--------|---------|-------|---------|
| `MYCA_A2A_ENABLED` | `true` | MAS | Enable A2A gateway (Agent Card, message/send). Set `false` to disable. |
| `MYCA_WEBMCP_ENABLED` | (enabled) | Website | Set `NEXT_PUBLIC_MYCA_WEBMCP_ENABLED=false` to disable WebMCP tool registration. |
| `MYCA_UCP_ENABLED` | `false` | MAS | Enable live UCP commerce calls when `UCP_BASE_URL` is set. |

## Protocol telemetry

All protocol events log with unified format:

```
protocol_event protocol=<a2a|webmcp|ucp> tool_name=<name> risk_flags=[...] [extra]
```

- **A2A**: `protocol=a2a`, `remote_agent`, `context_id`
- **UCP**: `protocol=ucp`, `tool_name` (discover, quote, checkout, order-status), `risk_flags` when risk_tier ≠ low

Logs appear in MAS stdout (or configured logging backend). Use `grep protocol_event` to filter.

## Staged rollout

### 1. Local + Sandbox validation

- Run protocol tests: `poetry run pytest tests/test_protocol_a2a.py tests/test_protocol_ucp.py -v`
- Website WebMCP: `npm run test -- tests/webmcp`
- All flags enabled by default locally. Verify A2A Agent Card, message/send, commerce discover/quote.

### 2. MAS VM enablement

- Set on MAS VM (192.168.0.188):
  - `MYCA_A2A_ENABLED=true`
  - `MYCA_UCP_ENABLED=false` (until UCP provider configured)
- Restart MAS: `sudo systemctl restart mas-orchestrator`
- Verify: `curl http://192.168.0.188:8001/.well-known/agent-card.json`

### 3. Website production enablement

- After CI + smoke checks pass:
  - Do **not** set `NEXT_PUBLIC_MYCA_WEBMCP_ENABLED=false` (WebMCP stays enabled when browser supports it)
  - Or set `false` to disable WebMCP until validated
- Deploy website with protocol proxy routes (`/api/myca/a2a/*`, `/api/mas/commerce/*`)

## Quick checks

| Check | Command |
|-------|---------|
| A2A Agent Card | `curl http://localhost:8001/.well-known/agent-card.json` |
| A2A message/send | `curl -X POST http://localhost:8001/a2a/v1/message/send -H "Content-Type: application/json" -d '{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"hello"}]}}'` |
| Commerce discover | `curl http://localhost:8001/api/commerce/discover` |
| Protocol tests | `poetry run pytest tests/test_protocol_a2a.py tests/test_protocol_ucp.py -v` |

## Troubleshooting

- **404 on Agent Card**: `MYCA_A2A_ENABLED=false` or A2A router not loaded. Check MAS logs.
- **WebMCP tools not registering**: `navigator.modelContext` requires Chrome 146+. Check `NEXT_PUBLIC_MYCA_WEBMCP_ENABLED`.
- **Commerce blocked**: Medium+ risk requires `approval_token`. Use `risk_tier=low` for discover/quote or provide token for checkout.

## Related docs

- `docs/MYCA_PROTOCOL_STACK_INTEGRATION_PLAN_FEB17_2026.md` – Full plan
- `mycosoft_mas/myca/ROUTER_POLICY.md` – A2A sanitization rules
