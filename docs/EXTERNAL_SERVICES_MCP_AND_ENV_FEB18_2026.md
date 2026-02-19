# External Services: MCP, Integrations, and Environment Variables

**Date:** February 18, 2026  
**Purpose:** Single reference for NCBI, ChemSpider, Asana, Notion, and Slack: MCP config, MAS integrations, env vars, and MYCA/agent usage.

---

## 1. Environment Variables (set in `.env`; never commit real values)

Set these in your local `.env` (or Cursor / shell environment) so MCP servers and MAS can use them. Copy from `.env.example` and fill in real values.

| Service    | Env var(s)           | Purpose |
|-----------|----------------------|---------|
| **NCBI**  | `NCBI_API_KEY`       | PubMed / GenBank E-utilities (10 req/sec with key) |
| **ChemSpider** | `CHEMSPIDER_API_KEY`, `CHEMSPIDER_API_URL` | RSC Compounds API (optional; default URL in .env.example) |
| **Asana** | `ASANA_API_KEY`, `ASANA_WORKSPACE_ID` | Tasks and projects |
| **Notion**| `NOTION_API_KEY`, `NOTION_DATABASE_ID` | Docs, databases, pages |
| **Slack** | `SLACK_OAUTH_TOKEN`  | Post messages, list channels |

**MINDEX DB (for sync scripts):**  
`MINDEX_DB_HOST`, `MINDEX_DB_PORT`, `MINDEX_DB_USER`, `MINDEX_DB_PASSWORD`, `MINDEX_DB_NAME` — used by `_full_mindex_sync.py` and `_quick_mindex_sync.py` (no hardcoded credentials).

---

## 2. MCP Servers (`.mcp.json`)

- **mycosoft-orchestrator** and **mycosoft-registry** receive these env vars when Cursor starts them:  
  `NOTION_API_KEY`, `NCBI_API_KEY`, `CHEMSPIDER_API_KEY`, `ASANA_API_KEY`, `ASANA_WORKSPACE_ID`, `SLACK_OAUTH_TOKEN`.  
  Cursor expands `${VAR}` from your environment.

- **Notion** MCP entry: optional stdio server using `NOTION_API_KEY` for Notion API access from Cursor. If the Notion MCP package is not installed, you can remove the `Notion` entry from `.mcp.json` or install the official Notion MCP server and set `NOTION_API_KEY` in your environment.

---

## 3. MAS Integrations (agents and MYCA)

| Service    | Client module                      | Used by |
|-----------|-------------------------------------|---------|
| **Notion**| `mycosoft_mas.integrations.notion_client.NotionClient` | notion-sync, documentation-manager, agents that push docs to Notion |
| **NCBI**  | `mycosoft_mas.integrations.ncbi_client.NCBIClient`    | ResearchAgent, MycologyBioAgent, MINDEX sync (PubMed/GenBank) |
| **ChemSpider** | `mycosoft_mas.integrations.chemspider_client.ChemSpiderClient` | LabAgent, scientific agents; MINDEX ETL has full implementation |
| **Asana** | `mycosoft_mas.integrations.asana_client.AsanaClient`  | SecretaryAgent, ProjectManagerAgent, n8n, MYCA task sync |
| **Slack** | `mycosoft_mas.integrations.slack_client.SlackClient`  | SecretaryAgent, n8n, MYCA notifications |

All clients read credentials from the environment (or optional config dict). No secrets in code.

---

## 4. Interaction with MYCA and Agents

- **Orchestrator / MYCA:** When the orchestrator or other MYCA components run (e.g. via MCP or on the MAS VM), they need the same env vars set on the **MAS VM** (188) or in the process that runs the orchestrator, so tasks that call NCBI, Notion, Asana, or Slack can succeed.

- **Agents that use these integrations:**  
  ResearchAgent, MycologyBioAgent (NCBI, ChemSpider); SecretaryAgent, ProjectManagerAgent (Asana, Slack); notion-sync and documentation-manager (Notion). Ensure `.env` on the MAS host (or Docker env) includes the keys if those agents run there.

- **Cursor MCP:** For Cursor-side MCP servers (mycosoft-orchestrator, mycosoft-registry, Notion), set the env vars in your **local** environment (e.g. Cursor settings, `.env` in MAS repo root, or shell) so `${NOTION_API_KEY}` etc. resolve when Cursor launches the MCP processes.

---

## 5. Where to Set Real Values

- **Local / Cursor:** In the MAS repo copy `.env.example` to `.env` and fill in real values. Ensure `.env` is in `.gitignore` (it is). Do not commit `.env`.
- **MAS VM (188):** Set the same variables in the environment used by the MAS container or systemd service (e.g. Docker `env` or a sourced `.env`).
- **Security:** Rotate any key that may have been committed or exposed. Prefer a secrets manager or CI secrets for production.

---

## 6. Related Docs

- `.env.example` — full list of MAS env vars including these five services and MINDEX DB.
- `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md` — MCP usage and sub-agent guidance.
- `docs/SECRET_MANAGEMENT_POLICY_FEB09_2026.md` — policy for secrets and env.
