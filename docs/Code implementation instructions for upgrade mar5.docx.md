# Mycosoft Coding Agent Instructions (March 5 2026)

This document consolidates all development tasks extracted from internal discussions, Notion plans and architecture documents. Use this as a single source of truth to implement features in the various Mycosoft repositories. Each task below includes a brief rationale and references to the source plans so that reviewers can trace requirements.

## Memory System Integration

### 1 Create MemoryCoordinator

* **Path:** mycosoft\_mas/memory/coordinator.py

* **Goal:** Centralize management of the six memory layers (ephemeral, session, working, semantic, episodic, system). The coordinator should provide a unified API for storing and retrieving events, and manage persistence using vector databases and PostgreSQL. See the “Memory Integration Plan – Feb 5 2026”[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md) and “MYCA Memory Architecture”[\[2\]](https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c#:~:text=Implemented%3A%20February%205%2C%202026%0A,Feb%205%2C%202026) for details.

* **Key functions:**

* store\_event(agent\_id, layer, data): write an observation or summary to a specific layer.

* retrieve\_events(agent\_id, layer, time\_window): return relevant events from the layer.

* compact\_memory(): periodic maintenance to purge expired data based on TTL (30 min for Ephemeral, 24 hr for Session, etc.).

### 2 Integrate Orchestrator with Memory

* **Files:** mycosoft\_mas/core/orchestrator.py

* **Goal:** Ensure the orchestrator logs all significant agent actions (assignments, context switches, failures) to the MemoryCoordinator and retrieves context for new tasks. This integration supports better context sharing across agents and voice sessions[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md).

* **Tasks:**

* Inject a MemoryCoordinator instance into the orchestrator at startup.

* On task assignment, call store\_event() with appropriate layer (e.g., Session) and details.

* When preparing context for an agent, call retrieve\_events() to build a summary.

### 3 Add AgentMemoryMixin

* **Files:** mycosoft\_mas/agents/memory\_mixin.py (new), modify agents/base\_agent.py.

* **Goal:** Provide shared logic for agents to store their observations and results. The mix‑in should offer convenience methods like recall\_recent() and store\_episode()[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md).

* **Implementation:**

* Inherit from this mix‑in in all agent classes.

* Automatically record decisions, outputs and environment data to the appropriate memory layers.

### 4 Voice & Workflow Memory Integration

* **Files:** voice/personaplex\_bridge.py, integrations/n8n\_client.py, core/routers/memory\_api.py.

* **Goal:** Persist voice session summaries and workflow execution traces to the memory system[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md). This ensures conversational context is available to agents and future sessions.

* **Tasks:**

* Modify the voice bridge to call MemoryCoordinator.store\_event() after each session or important exchange.

* Extend the n8n client to log workflow outputs, triggers and failures.

* Add new API endpoints (e.g., GET /memory/{agent\_id}/{layer}) to query memory layers for external tools.

### 5 Enhance Memory API

* **File:** core/routers/memory\_api.py.

* **Goal:** Provide robust endpoints to interact with memory:

* Filtering by agent, session ID and time.

* Streaming updates to support live dashboards.

* **Tasks:**

* Implement JSON schema for request/response bodies.

* Integrate with authentication middleware and add health checks.

### 6 Database Migrations & Bridges

* **Scripts:** Apply SQL migrations 013\_unified\_memory.sql, 014\_voice\_sessions.sql, 015\_workflow\_memory.sql, 016\_graph\_persistence.sql[\[2\]](https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c#:~:text=Implemented%3A%20February%205%2C%202026%0A,Feb%205%2C%202026).

* **Bridges:** Provide language‑specific adapters in memory\_bridge.ts, memory\_bridge.cs, and memory\_bridge.hpp so external systems (TypeScript, C\#, C++) can interact with memory[\[2\]](https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c#:~:text=Implemented%3A%20February%205%2C%202026%0A,Feb%205%2C%202026).

* **Knowledge Graph:** Ensure persistent\_graph.py persists relationships and reasoning traces; integrate this with the memory system.

### 7 Testing & Validation

* **File:** tests/test\_memory\_integration.py.

* **Goal:** Simulate orchestrator events, agent actions and voice workflows to verify correct storage and retrieval. Validate recovery time (RTO) and recovery point (RPO) objectives: both 1 hour[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md).

* **Tasks:**

* Use fixtures to create synthetic events and sessions.

* Assert that data is correctly stored in each memory layer.

* Measure retrieval performance and ensure it meets expectations.

## Infrastructure & Proxmox Deployment

### 1 VM Template & Creation Scripts

* **Scripts:** create\_template.sh, create\_vms.sh[\[3\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L95-L184).

* **Goal:** Automate creation of a base Ubuntu 24.04 template and cloning of VMs for each service (MINDEX, website, MAS, MycoBrain, monitoring, n8n, redis, qdrant). Use Proxmox API or qm CLI with parameterized variables for VM ID, CPU, memory, disk and VLAN tags.

### 2 Service Deployment Scripts

* **Tasks:** For each service (MINDEX, website, MAS orchestrator, MycoBrain) write a deployment script that:

* Clones the GitHub repo.

* Writes environment files (.env, .env.local) with secrets placeholders.

* Builds and starts the service using Docker Compose or docker run[\[4\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L216-L289).

* Parameterize API keys, DB credentials and network addresses.

### 3 High‑Availability & Monitoring

* **Systemd Services:** Create unit files (e.g., mycosoft-mindex.service) to ensure containers restart automatically[\[5\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L293-L317).

* **Prometheus:** Provide configuration (scrape configs) for each service and integrate with Grafana dashboards (system overview, MINDEX metrics, MycoBrain devices, website performance)[\[6\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L293-L344).

* **Alerting:** Configure Alertmanager with Slack and email receivers[\[7\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L387-L409).

### 4 Backups & Disaster Recovery

* **Scripts:** backup.sh for daily VM snapshots and configuration backup; mindex\_backup.sh for hourly PostgreSQL dumps[\[8\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L347-L380).

* **Retention:** Retain VM backups for seven days and DB backups for 24 hours; automate cleanup.

* **Recovery:** Document and script steps to restore VMs, restore database and verify service connectivity[\[9\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L455-L466).

### 5 Security Hardening

* **Firewall:** Implement iptables rules to allow only necessary inter‑VLAN traffic and drop all other inbound connections[\[10\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L415-L424).

* **TLS:** Automate SSL/TLS configuration using Let’s Encrypt for external services and mutual TLS for internal services[\[11\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L426-L431).

## System Architecture & Operations

### 1 Network & VLAN Configuration

* Encode VLAN definitions (10 – Internal, 20 – DMZ, 30 – Management, 40 – IoT) and IP assignments (e.g., mindex: 10.10.10.10) in infrastructure‑as‑code (e.g., Ansible, Terraform)[\[12\]](https://www.notion.so/2e51b1b5693481179274e6b9d0f1ea48#:~:text=%23%23%20VLAN%20Configuration%0A%3Ctable%20header,table)[\[13\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L81-L90).

* Ensure reproducible network setup during deployment.

### 2 Deployment Workflows

* Implement CI/CD pipelines or scripts that mirror the “Code Change Deployment” process: test locally, push to GitHub, SSH to VM, reset to origin/main, rebuild without cache, restart services, purge Cloudflare cache and verify sandbox environment[\[14\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=,sandbox.mycosoft.com%5D%28http%3A%2F%2Fsandbox.mycosoft.com).

* Provide a simplified “Media‑Only Deployment” workflow: copy files to NAS, restart website container, purge cache and verify assets[\[15\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=%23%23%23%20Media,Verify%20asset%20URLs).

### 3 Health Endpoints & Monitoring

* Implement and expose health endpoints for each service (e.g., /api/health for website, /health for MINDEX and MycoBrain) that return appropriate status codes or JSON responses[\[16\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=%3Ctable%20header).

* Add these endpoints to the Prometheus scrape configuration and write tests to validate their availability.

### 4 Request Flow Documentation

* Capture request flow diagrams as code comments or separate documentation describing how requests traverse Cloudflare, tunnels and VMs for website, MycoBrain API and media assets[\[17\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=,). This helps maintainers understand traffic patterns.

## General Notes

1. **Parameterization:** Where scripts include hard‑coded secrets (passwords, API keys), refactor to use environment variables or secret management tools. Provide sample .env.example files.

2. **Repository Structure:** Ensure new modules follow repository conventions, including appropriate \_\_init\_\_.py placement, test discovery and documentation.

3. **Documentation:** Add docstrings to all public functions, update README files and include links back to the relevant planning documents.

4. **Commit & Review:** Push your changes to dedicated branches (e.g., feat/memory-coordinator, feat/proxmox-automation) and create pull requests for each logical grouping of work so that senior developers can review and merge incrementally.

---

This file serves as a roadmap for the coding agent. By implementing these tasks across the Mycosoft repositories, you will operationalize the plans outlined in our internal discussions and documentation. Refer back to the cited pages for deeper context when necessary.

---

[\[1\]](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92#:~:text=,2026.md%60%5D%28http%3A%2F%2F2026.md) Memory Integration Plan \- Feb 5, 2026

[https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92](https://www.notion.so/2fe1b1b5693481e79680c8352fcf3b92)

[\[2\]](https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c#:~:text=Implemented%3A%20February%205%2C%202026%0A,Feb%205%2C%202026) MYCA Memory Architecture \- Feb 5, 2026

[https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c](https://www.notion.so/2fe1b1b5693481049f40ea78de402b7c)

[\[3\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L95-L184) [\[4\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L216-L289) [\[5\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L293-L317) [\[6\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L293-L344) [\[7\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L387-L409) [\[8\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L347-L380) [\[9\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L455-L466) [\[10\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L415-L424) [\[11\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L426-L431) [\[13\]](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md#L81-L90) PROXMOX\_DEPLOYMENT.md

[https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX\_DEPLOYMENT.md](https://github.com/MycosoftLabs/mycosoft-mas/blob/8e24d5d18334427865450aee3d3f210e7c1b6712/docs/PROXMOX_DEPLOYMENT.md)

[\[12\]](https://www.notion.so/2e51b1b5693481179274e6b9d0f1ea48#:~:text=%23%23%20VLAN%20Configuration%0A%3Ctable%20header,table) Proxmox Deployment Plan

[https://www.notion.so/2e51b1b5693481179274e6b9d0f1ea48](https://www.notion.so/2e51b1b5693481179274e6b9d0f1ea48)

[\[14\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=,sandbox.mycosoft.com%5D%28http%3A%2F%2Fsandbox.mycosoft.com) [\[15\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=%23%23%23%20Media,Verify%20asset%20URLs) [\[16\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=%3Ctable%20header) [\[17\]](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea#:~:text=,) System Architecture Overview \- January 2026

[https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea](https://www.notion.so/2f11b1b5693481ec9a04ec7857f799ea)