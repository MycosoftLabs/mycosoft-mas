# MYCA Security Boundary - May 14, 2026

## Invariants

- Chat text is never identity proof.
- Browser metadata is never authorization proof.
- Client-supplied `user_id`, `user_role`, `actor`, display names, and `is_morgan` are compatibility context only.
- Creator authority requires verified email `morgan@mycosoft.org` and role `owner` or `superuser`.
- Global learning, training, memory, policy, governance, override, and internal-system changes require verified owner or superuser authority.
- Search UI state must remain isolated from MYCA chat state unless a verified session explicitly links them.

## MAS-Side Enforcement

- Shared identity resolution lives in `mycosoft_mas/core/myca_identity.py`.
- Public MYCA chat, voice, memory, and search routes resolve identity server-side before using any user-scoped state.
- Anonymous users receive guest runtime context and anonymous/ephemeral memory namespaces.
- Cross-user memory/search access is denied unless the verified identity is `owner` or `superuser`.
- Impersonation claims and privileged intents are logged through the MYCA security audit helper.

## Internal Service Contract

Website, MINDEX, and other internal services must forward verified identity with:

- `X-MYCA-Service-Token`
- `X-MYCA-Verified-User-Id`
- `X-MYCA-Verified-Email`
- `X-MYCA-Verified-Role`

`X-MYCA-Service-Token` must match `MYCA_INTERNAL_SERVICE_TOKEN` in MAS. Unsigned identity forwarding is treated as anonymous.

## Operational Evidence

- `/health` now includes MYCA route mount evidence.
- `/myca/route-mounts` reports consciousness, grounding, memory, search, and voice route availability.
- MYCA gateway `/sessions` returns daemon/task state instead of a placeholder.
- `scripts/check_myca_channels.py` verifies configured channel readiness without printing secret values.
- `scripts/check_myca_workflow_drift.py` fails when `n8n/workflows` and `workflows/n8n` drift.
