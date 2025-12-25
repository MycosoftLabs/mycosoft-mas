MYCA n8n Credential Governance
==============================

Never commit secrets. Keep all credentials in Vault (or an equivalent secret manager) and inject them into n8n at runtime.

Patterns
- Vault Agent template → env vars: render short-lived tokens into `N8N_`/`MYCA_` env vars consumed by credential placeholders.
- n8n credentials: create credentials in the UI that read from env variables only (no static secrets in JSON exports).
- Least privilege: create separate credentials per scope: `*-ro` read-only, `*-rw` write, `*-admin` admin/destructive.
- Rotation: rotate tokens via Vault and restart the n8n service or refresh credentials.

Required environment variables (examples)
These are placeholders—set them via Vault Agent or your secret injector:
- `VAULT_ADDR`, `VAULT_TOKEN` (or approle envs `VAULT_ROLE_ID`, `VAULT_SECRET_ID`)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GEMINI_KEY`
- `SLACK_TOKEN`, `TELEGRAM_BOT_TOKEN`, `DISCORD_WEBHOOK_URL`
- `GITHUB_TOKEN`, `GITLAB_TOKEN`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `STRIPE_SECRET_KEY`, `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`
- `SENTRY_TOKEN`, `PAGERDUTY_TOKEN`, `SPLUNK_HEC_TOKEN`

Reference these in n8n credential fields as `{{$env.<ENV_VAR_NAME>}}`.

Bootstrap flow
1) Vault Agent (or SSM/Secrets Manager) renders env vars into the n8n container.  
2) n8n credentials are configured to read only from env vars.  
3) Workflows use credentials by name; exports remain secret-free.

Auditing
- All workflows emit audit events via `14_audit_logger.json`.
- Audit payload includes: timestamp, workflow_id, actor, target integration, request hash, response hash, status, duration_ms.

Safety guardrails
- Destructive actions require `confirm=true` and are double-checked in router and confirmation gate.
- Credentials are segmented per integration and scope to reduce blast radius.

Adding a new credential safely
1) Create/rotate secret in Vault.  
2) Map Vault secret → env var via Agent template.  
3) In n8n UI, create credential that references the env var.  
4) Update `/registry/integration_registry.json` with the new integration and risk scope.  
5) Test via `/myca/command` using the new integration.
