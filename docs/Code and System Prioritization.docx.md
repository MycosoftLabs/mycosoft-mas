# Mycosoft system priorities and integration roadmap (February 9 2026)

## 1. Summary of current system

* **Repositories and deployed services** – The Mycosoft ecosystem spans six separate repositories. The mycosoft‑mas repository contains the MAS orchestrator and integration layer, while the website repository holds the production Next.js application for the Mycosoft site. The mindex repository provides a FastAPI service exposing endpoints for taxonomic data, observations and device integration (Wi‑Fi sense, drone integrations, etc.). Additional repositories include **MycoBrain** (ESP32 firmware and device tools), **NatureOS** (device integration and Earth‑simulator schemas) and **platform‑infra** (infrastructure scripts). A full system audit found that the MAS repo contains many intentionally empty directories – real implementation lives in the other repositories – and that the integration code is fragmented[\[1\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,Minimal).

* **Existing integrations** – The website calls the MINDEX API to fetch species data and uses MapLibre/Three.js for interactive dashboards. The MAS orchestrator (Python/FastAPI) exposes an agent runtime, memory coordinator and voice system. NatureOS uses a Next.js frontend with Python collectors. Many integration points are still manual or missing (e.g., species pages fallback to mock data when the MINDEX API is unavailable[\[2\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=%23%23%23%202.2%20Fix%20Website,2.3%20Populate%20Species%20Database)).

* **Testing & CI/CD** – Some repositories contain ad‑hoc test scripts (e.g., test\_services.py in the website repo) and there are smoke tests for the MINDEX API. The MAS repo contains a GitHub Actions workflow (dependencies.yml) that installs dependencies, runs tox tests, performs security audits and creates an SBOM[\[3\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/5f1046839e2ba9ccfa9a92faa6d4cd8b58c72716/.github/workflows/dependencies.yml#L24-L65). However, there is no unified CI pipeline across all repositories, no automated end‑to‑end integration tests, and no systematic code review process.

* **Security & secret management** – Secrets (API keys, database passwords) are sometimes hard‑coded or stored in environment files in local repos, with inconsistent rotation. A recent audit of the ClawHub marketplace found **341 malicious skills out of 2 857 total (≈11.9 %)**, most of which install malware (Atomic Stealer) via fake prerequisites[\[4\]](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html#:~:text=A%20security%20audit%20of%202%2C857,to%20new%20supply%20chain%20risks). These skills exfiltrate credentials and keys by convincing users to run obfuscated shell scripts[\[5\]](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html#:~:text=Present%20within%20the%20password,controlled%20infrastructure). Because Mycosoft plans to integrate external skills from open‑source marketplaces, a robust malware‑scanning and allow‑listing process is essential.

* **Documentation** – A new Notion database ("Mycosoft Documentation") aggregates markdown files from all repositories. It categorizes documents by **Category** (Architecture, Integration, Memory, Security, etc.), **Repo**, and **Source Type** (Documentation, Plan). Numerous integration and implementation plans live here.

## 2. High‑priority projects from recent plans

The following items originate from the **Cursor Plans** in Notion and from internal documentation. Tasks are grouped by priority (P0 immediate, P1 next sprint, P2 future) and by domain.

### 2.1 System‑wide audit and consolidation (P0)

| Task | Rationale | References & implementation |
| :---- | :---- | :---- |
| **Create a master architecture document and consolidate repositories** | The full system audit revealed six repositories with unclear relationships and many empty directories. Creating a unified architecture map and adding README/symlink files to empty directories in mycosoft‑mas will help developers navigate the codebase[\[6\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,or%20symlink%20to%20actual%20locations). | Add a high‑level diagram (Mermaid) showing how the Website, MAS, MINDEX API, MycoBrain firmware, NatureOS and infrastructure interact[\[7\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,MYCOBRAIN). Place README files in empty dirs explaining where the actual code resides. Update the Notion database with this document. |
| **Sync all documentation to Notion** | Many markdown files in the repos are not reflected in the Notion knowledge base. The audit plan directs scanning all .md files and uploading them by category[\[8\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,Architecture%2C%20Firmware%2C%20API%2C%20Debugging%2C%20History). | Automate Notion sync using the Notion API from the MAS repository (scripts exist in docs/NOTION\_SYNC\_SETUP.md). Schedule daily sync via CI pipeline. |
| **Verify and migrate MINDEX** | Ensure the MINDEX API is running and connected to PostgreSQL, then run database migrations and full fungal species sync[\[9\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,MINDEX%20Connection). Update website environment variables so species pages use the live API instead of mock data[\[2\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=%23%23%23%202.2%20Fix%20Website,2.3%20Populate%20Species%20Database). | Write a health‑check script (curl /docs endpoint) and incorporate it into CI. |
| **Document and register all MAS agents** | Over 42 agents exist in the MAS runtime. Create a registry with descriptions, responsibilities and integration points[\[10\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,status%3A%20completed). | Add agents\_registry.md in the MAS repo summarising each agent. Link this registry in the website dashboard so developers can explore capabilities. |
| **Production migration plan** | Create a Proxmox VM deployment plan for 24/7 operation[\[11\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,sync). Include rollback procedures, environment variable management and data backup steps. | Document container images, network topology, and secrets rotation. Provide a runbook for migrating from development to production. |

### 2.2 Data & visualization enhancements (P0–P1)

| Task | Rationale | References & implementation |
| :---- | :---- | :---- |
| **Integrate new genomic/spatial visualization tools** | The Tool Integration Priority Plan recommends adding Gosling.js (genome grammar), pyCirclize (circular plots) and Vitessce (single‑cell/spatial visualization) to the website for MINDEX data[\[12\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=,4%20days). | *Implementation*: add Gosling.js and Vitessce to package.json and create new pages/components (e.g., app/natureos/mindex/explorer.tsx and components/mindex/). Add a backend route /api/mindex/visualization/circos that uses pyCirclize to generate SVG/PNG for gene networks[\[13\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%202.%20pyCirclize%20,Ancestry%20page%20phylogenetic%20circular%20trees). These are top priorities (P0) because they make MINDEX data visible to users. |
| **Implement JBrowse2 genome browser** | A P1 priority; offers a full genome browser for species comparisons[\[14\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%206.%20JBrowse2%20,5%20days). | Create a React wrapper component for JBrowse2 and integrate into the MINDEX species pages. Evaluate integration with iNaturalist observation data. |
| **Evaluate LangGraph for agent orchestration** | The P1 plan proposes a proof‑of‑concept using the LangGraph library to orchestrate multiple agents and compare performance with the existing FastAPI orchestrator[\[15\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%204.%20LangGraph%20,Document%20integration%20path%20if%20viable). | Build a simple LangGraph demo with three agents, benchmark task throughput and state management, and write an evaluation report recommending adoption or not. |
| **Add Transformer‑Explainer to the AI Studio** | This tool helps users understand transformer decisions. It will be embedded in /natureos/ai-studio/explainer[\[16\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%205.%20Transformer%20Explainer%0A%5C%2A%5C%2ASource%5C%2A%5C%2A%3A%20%5C%5Bpoloclub.github.io%2Ftransformer,embed%2Fiframe%20or%20port%20components). | Copy or embed the open‑source UI, link to Mycosoft training examples, and provide documentation on how to interpret results. |
| **Integrate Packery and Perspective** | The integration plan identifies Packery (draggable dashboard grid) and Perspective (real‑time analytic tables) as Tier 2 tasks with significant impact[\[17\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,grid.tsx). | Create reusable React components (packery-grid.tsx and perspective-table.tsx) and update the CREP and NatureOS dashboards to use them. Save user preferences in Supabase. |
| **Implement JSON‑render for AI‑generated widgets** | Tier 3; allows MYCA to generate interactive dashboards via chat[\[18\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=%23%23%23%20TIER%203%3A%20BACKEND%2FDEVOPS%20,New%20Docker%20container%20definition). | Build an inventory of available React components and implement an API that accepts a JSON spec and renders widgets accordingly. |
| **Enhance research ingestion pipeline** | The plan recommends using zpdf to extract text from PDFs and feeding it into MINDEX, along with tools like maptoposter for map generation[\[19\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,MINDEX%20via%20existing%20ingestion%20pipeline). | Build a Node.js wrapper around the Zig zpdf binary, integrate it into app/api/scrapers/, and connect the output to MINDEX ingestion. |

### 2.3 Memory and AI system improvements (P0–P1)

| Task | Rationale | References & implementation |
| :---- | :---- | :---- |
| **Complete Memory UI integration** | The memory integration plan lists missing UI components: summary cards, knowledge graph viewer, user profile widget, brain status widget, episodic memory viewer and memory management panel[\[20\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=,with%20export%2Fcleanup%20actions). All backend endpoints already exist[\[21\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4). | Implement new widgets (BrainStatusWidget, UserProfileWidget, EpisodicMemoryViewer, KnowledgeGraphViewer and MemoryManagementPanel) in the unifi-dashboard/src/components/widgets/memory/ directory and proxy the MAS brain endpoints under /api/brain/[\[22\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=,Phase%202%3A%20New%20UI%20Components). Connect summary cards to /api/memory/stats data and add a real‑time memory health indicator on the dashboard[\[23\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C%2A%5C%2AProblem%5C%2A%5C%2A%3A%20No%20real,Memory%20Export%2FCleanup%20Tools%20%28Missing). |
| **Expose brain context to voice system** | The plan mentions new endpoints /voice/brain/status and /voice/brain/context/{user\_id}; the UI currently lacks integration[\[24\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,Memory%20Health%20Monitor%20%28Missing). | Create a useBrain hook to fetch brain status and context, and update the voice interface to display memory context. |
| **Implement memory export/cleanup tools** | Provide UI controls to export memory to JSON, import from backup, and clean up old memories[\[25\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,with%20export%2Fcleanup%20actions). | Use existing backend scripts (memory/export.py, cleanup.py), wrap them in FastAPI endpoints, and build a simple management panel with confirm dialogs. |
| **Enhance conversation history** | Add session metadata (start/end time, agents involved) to conversation transcripts and allow filtering by event type[\[26\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,with%20session%20details%20panel). | Extend the ConversationHistory component and update the VoiceSessionStore to include metadata. |

### 2.4 Integration of external GitHub projects (P1–P2)

The **Mycosoft Integration Plan** analyzed \~20 GitHub projects and categorized them by priority. Below are key recommendations:

| Tier  | Projects | Why/Use‑cases | Implementation notes |
| :---- | :---- | :---- | :---- |
| **Tier 1 (immediate)** | **itshover** – animated icons; **Clusterize.js** – efficient scrolling for large tables; **Nodemailer** – transactional emails[\[27\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,). | Drop‑in UI enhancements; immediate value without major risk. | Replace Lucide icons in headers and buttons with itshover icons. Use Clusterize.js in CREP/MINDEX data tables and the NatureOS dashboards. Create a lib/email/ module to wrap Nodemailer for notifications (user signup, error alerts). |
| **Tier 2 (medium‑term)** | **Packery** – draggable dashboard grid; **Perspective** – real‑time data tables; **json‑render** – AI‑generated dashboards[\[28\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,added%20as%20new%20components%20in). | Improves user customization and analytics capabilities. | Build React wrappers for these libraries and integrate into the dashboards. For json‑render, design a safe component registry so only approved components can be rendered from JSON. |
| **Tier 3 (backend & devops)** | **xyOps** – workflow scheduler; **disable‑cloudflare‑cli** – DNS proxy mgmt; **port‑killer** – local port management; **TONL** – LLM token compression[\[29\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=%23%23%23%20TIER%203%3A%20BACKEND%2FDEVOPS%20,45%25%20token%20cost%20reduction). | Infrastructure improvements and developer productivity. | Deploy xyOps as a separate container, connect to Grafana/Prometheus for scheduling and monitoring, and migrate existing cron jobs. Use TONL in the MYCA inference pipeline to reduce token costs. The other tools are low‑priority developer conveniences. |
| **Tier 4 (research)** | **zpdf** for PDF extraction, **maptoposter** for map generation, **history** (globe UI)[\[30\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,MINDEX%20via%20existing%20ingestion%20pipeline). | Data ingestion and exploratory visualizations. | Build Node/Python wrappers for zpdf and maptoposter as described above. The globe UI is inspiration for future Earth‑simulation UIs. |
| **Not recommended** | Projects like sbox-public (game engine) or the experimental Zen language offer little direct value[\[31\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,). | Avoid to stay focused on core platform development. | — |

### 2.5 Security hardening (P0–P1)

| Task | Rationale | References & implementation |
| :---- | :---- | :---- |
| **Implement an automated malware‑scanning pipeline for skills** | The Koi Security audit revealed that \~341 of 2 857 skills on ClawHub (≈11.9 %) were malicious and delivered the Atomic Stealer via fake prerequisites[\[4\]](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html#:~:text=A%20security%20audit%20of%202%2C857,to%20new%20supply%20chain%20risks). Mycosoft intends to integrate community skills, so it must not trust third‑party code blindly. | *Develop a scanning function*: (1) fetch each skill’s source repository; (2) run a static analysis to detect obfuscated shell commands, suspicious network calls (e.g., curl/wget to unknown domains), decode Base64 strings and search for known malware signatures; (3) check dependencies against a blacklist of known malicious packages; (4) generate a report and only allow skills that pass. Use VirusTotal’s API or open‑source scanners such as pip‑audit/clamav to evaluate dependencies; integrate this into the MAS deployment pipeline. |
| **Create a skill allow‑list/deny‑list** | Maintain a registry of approved skills with metadata (version, source, purpose, last audit date). Mark suspicious skills as denied and log the reason. | Include this registry in the MAS repository and expose it via the orchestrator so that agents can only load allowed skills. |
| **Improve secret management** | Move secrets to environment variables managed by a secret‑management service (e.g., HashiCorp Vault or AWS Secrets Manager). Rotate keys regularly and avoid committing .env files. | Use a .env.example file to document required variables and update the CI pipeline to inject secrets securely. |
| **Audit dependencies continuously** | Use the existing MAS GitHub workflow as a template: run pip‑audit/npm audit on each push, generate a Software Bill of Materials, and fail builds when vulnerabilities are found[\[3\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/5f1046839e2ba9ccfa9a92faa6d4cd8b58c72716/.github/workflows/dependencies.yml#L24-L65). | Add similar workflows to the website, MINDEX and NatureOS repos. |
| **Penetration testing & threat modeling** | Perform regular penetration tests of the website and APIs. Model potential attack vectors (SQL injection, privilege escalation, cross‑site scripting). For IoT devices (MycoBrain), ensure firmware updates are signed and that network traffic is encrypted. | Write a security report summarising vulnerabilities and mitigation actions. |

### 2.6 Development processes and tooling (P0–P2)

| Task | Rationale | Implementation suggestions |
| :---- | :---- | :---- |
| **Establish automated test suites** | The audit observed that many features lack integration tests, and some test scripts are manual (e.g., test\_services.py in the website repo). Comprehensive test coverage is essential for reliability. | Adopt Jest/Playwright for frontend unit and browser tests, PyTest for backend services, and Postman or pytest-httpx for API endpoints. Create test data fixtures and run tests in CI. Add code coverage thresholds and enforce them in pull requests. |
| **Implement unified CI/CD pipelines** | Only the MAS repo has a GitHub Actions workflow. Add pipelines to all repos to run tests, lint code, build Docker images and deploy to staging. | Use GitHub Actions templates for Node.js and Python. Integrate with Supabase and Proxmox for automated deployments and enable rollback via versioned Docker tags. |
| **Introduce code review and branching strategy** | Currently there is no formal code review or branching process. | Adopt GitFlow or trunk‑based development with feature branches. Require pull‑request reviews before merging. Use commit linting and semantic versioning to maintain consistent release notes. |
| **Dataset versioning and reproducibility** | Data ingested into MINDEX (e.g., species data from iNaturalist/GBIF) should be versioned to reproduce experiments. | Use DVC (Data Version Control) or the Supabase storage features to version datasets. Tag each dataset with a version and record the script and parameters used to generate it. |
| **Automate rollback and migrations** | The audit notes no rollback plans. Create migrations for database schema changes (Alembic for FastAPI), maintain a CHANGELOG.md, and script rollback steps. | Add migration checks to CI. For the website, implement canary deployments so new builds can be rolled back quickly if issues arise. |
| **Living documents and probabilistic engagement** | The user’s notes mention that knowledge should compound and that agents should have permission gates instead of constant approval. Agents should run autonomously but block harmful outputs. | Build auto‑updating documentation (e.g., dashboards that reflect current system state). For agent actions, implement a policy engine that allows high‑confidence actions but requires review when risk is detected (e.g., sending emails or updating databases). Randomize maintenance tasks (e.g., data refresh) to distribute load and avoid predictable patterns. |

## 3. Guidance on external projects and models

* **agent‑browser (vercel‑labs)** – A Rust CLI for headless browser automation. It supports commands like opening pages, clicking, typing and taking snapshots[\[32\]](https://raw.githubusercontent.com/vercel-labs/agent-browser/main/README.md#:~:text=agent). It could be used for automated browser tests and scraping tasks within MAS (e.g., verifying dashboard features). Integrate by adding a wrapper script and binding it as a skill.

* **HashiCorp agent‑skills** – Provides skills for interacting with HashiCorp products (Terraform, Packer). These can assist in infrastructure automation if Mycosoft uses these tools[\[33\]](https://raw.githubusercontent.com/hashicorp/agent-skills/main/README.md#:~:text=,with%20HCP%20Packer%20registry). Use them carefully after auditing for security issues.

* **Claude‑subconscious plugin** – Adds a persistent memory layer to Claude Code by observing sessions and injecting context[\[34\]](https://raw.githubusercontent.com/letta-ai/claude-subconscious/main/README.md#:~:text=). This could inspire enhancements to Mycosoft’s memory coordinator; however, it is designed for a different platform.

* **Step3‑VL‑10B** – A 10‑B parameter multimodal model offering strong vision‑language capabilities[\[35\]](https://raw.githubusercontent.com/stepfun-ai/Step3-VL-10B/main/README.md#:~:text=). If integrated, it could power computer‑vision tasks (e.g., species recognition from images) but requires significant resources. Evaluate when infrastructure is ready.

* **beautiful‑mermaid** – Renders Mermaid diagrams as SVG or ASCII art[\[36\]](https://raw.githubusercontent.com/lukilabs/beautiful-mermaid/main/README.md#:~:text=). This library can improve documentation and dashboards by rendering diagrams (e.g., the architecture maps above). Use in the UI to display dynamic system diagrams.

* **awesome‑openclaw‑skills** – Catalogues over 2 k OpenClaw skills with category filters and includes a blacklist of malicious skills[\[37\]](https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md#:~:text=OpenClaw%27s%20public%20registry%20,Here%27s%20what%20we%20filtered%20out). Use it as a starting point for building the skill allow‑list/deny‑list and for scanning new skills.

* **Other referenced articles** – Articles such as Tom’s Hardware piece on repurposing telephone wiring and Nature’s article on AlphaGenome may inspire hardware upgrades and variant effect prediction capabilities but are not directly actionable. Keep them in the knowledge base for future research.

## 4. Next steps and execution order

1. **Finalize the architecture consolidation and documentation (week 1)** – Create the master architecture diagram, add explanatory README files, and sync all docs to Notion. Ensure MINDEX is running and species data is populated. Develop the skill registry and update environment variables.

2. **Start integrating P0 visualization tools and memory UI (week 1–2)** – Install Gosling.js, pyCirclize and Vitessce, create the MINDEX explorer page, implement summary cards, BrainStatusWidget and related memory widgets. Begin the malware‑scanning pipeline implementation.

3. **Plan and implement CI/CD (week 2–3)** – Define testing strategy, add GitHub Actions for website, MINDEX and NatureOS, and centralize secrets management. Establish code review guidelines and a branching model.

4. **Evaluate and integrate P1 tools (week 3–4)** – Complete the LangGraph evaluation, JBrowse2 integration, Packery & Perspective components, and implement TONL for token compression. Conduct penetration tests and update security documentation.

5. **Prepare for future road‑map (week 5+)** – Investigate advanced visualization tools (IGV.js, HiGlass), research ingestion pipeline improvements and developer tools. Explore adoption of the Step3‑VL‑10B model for vision tasks and refine memory and AI enhancements.

---

---

[\[1\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,Minimal) [\[2\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=%23%23%23%202.2%20Fix%20Website,2.3%20Populate%20Species%20Database) [\[6\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,or%20symlink%20to%20actual%20locations) [\[7\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,MYCOBRAIN) [\[8\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,Architecture%2C%20Firmware%2C%20API%2C%20Debugging%2C%20History) [\[9\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,MINDEX%20Connection) [\[10\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,status%3A%20completed) [\[11\]](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47#:~:text=,sync) full\_system\_audit\_plan\_0d71a4a4.plan (synced 2026-02-08)

[https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47](https://www.notion.so/3021b1b5693481ee9788ce1be26c8c47)

[\[3\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/5f1046839e2ba9ccfa9a92faa6d4cd8b58c72716/.github/workflows/dependencies.yml#L24-L65) dependencies.yml

[https://github.com/MycosoftLabs/mycosoft-mas/blob/5f1046839e2ba9ccfa9a92faa6d4cd8b58c72716/.github/workflows/dependencies.yml](https://github.com/MycosoftLabs/mycosoft-mas/blob/5f1046839e2ba9ccfa9a92faa6d4cd8b58c72716/.github/workflows/dependencies.yml)

[\[4\]](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html#:~:text=A%20security%20audit%20of%202%2C857,to%20new%20supply%20chain%20risks) [\[5\]](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html#:~:text=Present%20within%20the%20password,controlled%20infrastructure) Researchers Find 341 Malicious ClawHub Skills Stealing Data from OpenClaw Users

[https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html)

[\[12\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=,4%20days) [\[13\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%202.%20pyCirclize%20,Ancestry%20page%20phylogenetic%20circular%20trees) [\[14\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%206.%20JBrowse2%20,5%20days) [\[15\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%204.%20LangGraph%20,Document%20integration%20path%20if%20viable) [\[16\]](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87#:~:text=%23%23%23%205.%20Transformer%20Explainer%0A%5C%2A%5C%2ASource%5C%2A%5C%2A%3A%20%5C%5Bpoloclub.github.io%2Ftransformer,embed%2Fiframe%20or%20port%20components) tool\_integration\_priority\_plan\_9a106511.plan (synced 2026-02-08)

[https://www.notion.so/3021b1b569348166ba9ac2908adc2a87](https://www.notion.so/3021b1b569348166ba9ac2908adc2a87)

[\[17\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,grid.tsx) [\[18\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=%23%23%23%20TIER%203%3A%20BACKEND%2FDEVOPS%20,New%20Docker%20container%20definition) [\[19\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,MINDEX%20via%20existing%20ingestion%20pipeline) [\[27\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,) [\[28\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,added%20as%20new%20components%20in) [\[29\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=%23%23%23%20TIER%203%3A%20BACKEND%2FDEVOPS%20,45%25%20token%20cost%20reduction) [\[30\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,MINDEX%20via%20existing%20ingestion%20pipeline) [\[31\]](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11#:~:text=,) mycosoft\_integration\_plan\_32d08104.plan (synced 2026-02-08)

[https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11](https://www.notion.so/3021b1b5693481b6bab0cf7d8e53ea11)

[\[20\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=,with%20export%2Fcleanup%20actions) [\[21\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4) [\[22\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=,Phase%202%3A%20New%20UI%20Components) [\[23\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C%2A%5C%2AProblem%5C%2A%5C%2A%3A%20No%20real,Memory%20Export%2FCleanup%20Tools%20%28Missing) [\[24\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,Memory%20Health%20Monitor%20%28Missing) [\[25\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,with%20export%2Fcleanup%20actions) [\[26\]](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4#:~:text=%5C,with%20session%20details%20panel) memory\_ui\_integration\_a21a0169.plan (synced 2026-02-08)

[https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4](https://www.notion.so/3021b1b56934816f9ed4cadfdb2174c4)

[\[32\]](https://raw.githubusercontent.com/vercel-labs/agent-browser/main/README.md#:~:text=agent) raw.githubusercontent.com

[https://raw.githubusercontent.com/vercel-labs/agent-browser/main/README.md](https://raw.githubusercontent.com/vercel-labs/agent-browser/main/README.md)

[\[33\]](https://raw.githubusercontent.com/hashicorp/agent-skills/main/README.md#:~:text=,with%20HCP%20Packer%20registry) raw.githubusercontent.com

[https://raw.githubusercontent.com/hashicorp/agent-skills/main/README.md](https://raw.githubusercontent.com/hashicorp/agent-skills/main/README.md)

[\[34\]](https://raw.githubusercontent.com/letta-ai/claude-subconscious/main/README.md#:~:text=) raw.githubusercontent.com

[https://raw.githubusercontent.com/letta-ai/claude-subconscious/main/README.md](https://raw.githubusercontent.com/letta-ai/claude-subconscious/main/README.md)

[\[35\]](https://raw.githubusercontent.com/stepfun-ai/Step3-VL-10B/main/README.md#:~:text=) raw.githubusercontent.com

[https://raw.githubusercontent.com/stepfun-ai/Step3-VL-10B/main/README.md](https://raw.githubusercontent.com/stepfun-ai/Step3-VL-10B/main/README.md)

[\[36\]](https://raw.githubusercontent.com/lukilabs/beautiful-mermaid/main/README.md#:~:text=) raw.githubusercontent.com

[https://raw.githubusercontent.com/lukilabs/beautiful-mermaid/main/README.md](https://raw.githubusercontent.com/lukilabs/beautiful-mermaid/main/README.md)

[\[37\]](https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md#:~:text=OpenClaw%27s%20public%20registry%20,Here%27s%20what%20we%20filtered%20out) raw.githubusercontent.com

[https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md](https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md)