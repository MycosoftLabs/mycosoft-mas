# MYCA Export Package — Skills Directory

**Export Date:** MAR16_2026  
**Purpose:** Individual skill documents for external AI systems (Base44, Claude, Perplexity, OpenAI, Grok). Each skill enables MYCA to perform specific operations within the Mycosoft ecosystem.

## Skills Included

| Skill | File | When to Use |
|-------|------|-------------|
| create-api-endpoint | `MYCA_EXPORT_SKILL_create-api-endpoint_MAR16_2026.md` | Adding new FastAPI endpoints to MAS |
| create-api-route | `MYCA_EXPORT_SKILL_create-api-route_MAR16_2026.md` | Adding Next.js API routes to website |
| create-integration-client | `MYCA_EXPORT_SKILL_create-integration-client_MAR16_2026.md` | Adding external service integrations |
| create-mas-agent | `MYCA_EXPORT_SKILL_create-mas-agent_MAR16_2026.md` | Creating new MAS agents |
| create-nextjs-page | `MYCA_EXPORT_SKILL_create-nextjs-page_MAR16_2026.md` | Adding new website pages |
| create-react-component | `MYCA_EXPORT_SKILL_create-react-component_MAR16_2026.md` | Building UI components |
| database-migration | `MYCA_EXPORT_SKILL_database-migration_MAR16_2026.md` | Modifying MINDEX database schema |
| deploy-mas-service | `MYCA_EXPORT_SKILL_deploy-mas-service_MAR16_2026.md` | Deploying MAS to VM 188 |
| deploy-mindex | `MYCA_EXPORT_SKILL_deploy-mindex_MAR16_2026.md` | Deploying MINDEX to VM 189 |
| deploy-website-sandbox | `MYCA_EXPORT_SKILL_deploy-website-sandbox_MAR16_2026.md` | Deploying website to Sandbox VM 187 |
| docker-troubleshoot | `MYCA_EXPORT_SKILL_docker-troubleshoot_MAR16_2026.md` | Debugging Docker container issues |
| gpu-node-deploy | `MYCA_EXPORT_SKILL_gpu-node-deploy_MAR16_2026.md` | Deploying GPU workloads to VM 190 |
| mobile-audit | `MYCA_EXPORT_SKILL_mobile-audit_MAR16_2026.md` | Auditing/fixing mobile responsiveness |
| neuromorphic-integration | `MYCA_EXPORT_SKILL_neuromorphic-integration_MAR16_2026.md` | Adding neuromorphic UI styling |
| run-system-tests | `MYCA_EXPORT_SKILL_run-system-tests_MAR16_2026.md` | Running comprehensive system tests |
| security-audit | `MYCA_EXPORT_SKILL_security-audit_MAR16_2026.md` | Security auditing |
| session-summarize | `MYCA_EXPORT_SKILL_session-summarize_MAR16_2026.md` | Compressing long threads for handoff |
| setup-env-vars | `MYCA_EXPORT_SKILL_setup-env-vars_MAR16_2026.md` | Configuring environment variables |
| start-dev-website | `MYCA_EXPORT_SKILL_start-dev-website_MAR16_2026.md` | Starting website dev server |
| update-registries | `MYCA_EXPORT_SKILL_update-registries_MAR16_2026.md` | Updating system registries |
| vm-health-check | `MYCA_EXPORT_SKILL_vm-health-check_MAR16_2026.md` | Checking VM and service health |
| workflow-orchestration | `MYCA_EXPORT_SKILL_workflow-orchestration_MAR16_2026.md` | Plan-first, verify-first execution |

## Usage for External Systems

1. **Load on demand** — When the user's request matches a skill's trigger, load that skill document into context.
2. **RAG retrieval** — Index all skill documents; retrieve relevant skills by semantic similarity to the query.
3. **Full context** — For maximum capability, load Identity + Soul + Constitution + all skills into the system prompt (context permitting).
