# VM Layout: Four Nodes (187, 188, 189, 190) – Feb 9, 2026

## Canonical assignment

Each major system has **its own VM**:

| VM    | IP             | Role                          | Key services / ports                    |
|-------|----------------|-------------------------------|-----------------------------------------|
| **Sandbox** | 192.168.0.187 | Website, MycoBrain host       | Website 3000, MycoBrain 8003            |
| **MAS**     | 192.168.0.188 | Multi-Agent System            | Orchestrator 8001, n8n 5678, Ollama 11434 |
| **MINDEX**  | 192.168.0.189 | Database + vector store       | Postgres 5432, Redis 6379, Qdrant 6333, MINDEX API 8000 |
| **GPU node**| 192.168.0.190 | GPU workloads                 | Voice, Earth2, inference (ports TBD)    |

- **187** = Sandbox only (website container, MycoBrain service on host).
- **188** = MAS only (orchestrator, agents, n8n, Ollama).
- **189** = MINDEX only (Postgres, Redis, Qdrant, MINDEX API).
- **190** = GPU node (new); use for heavy GPU services when moved off dev/local.

## Reference

- Rule: `.cursor/rules/vm-layout-and-dev-remote-services.mdc`
- CLAUDE.md System Architecture table
- Process registry: `.cursor/rules/python-process-registry.mdc` (VM SERVICES table)
