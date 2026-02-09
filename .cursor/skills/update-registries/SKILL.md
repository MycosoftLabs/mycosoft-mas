---
name: update-registries
description: Update Mycosoft system registries after code changes. Use after adding agents, API endpoints, services, devices, or documentation.
---

# Update System Registries

After making code changes that add or modify agents, APIs, services, devices, or documentation, update the relevant registries.

## Registries to Update

| Registry | File | When to Update |
|----------|------|----------------|
| Master Doc Index | `docs/MASTER_DOCUMENT_INDEX.md` | New docs created |
| System Registry | `docs/SYSTEM_REGISTRY_FEB04_2026.md` | New agents, services, devices |
| API Catalog | `docs/API_CATALOG_FEB04_2026.md` | New API endpoints |
| System Map | `docs/system_map.md` | Architecture changes |
| Memory Docs Index | `docs/MEMORY_DOCUMENTATION_INDEX_FEB05_2026.md` | Memory system changes |

## When Adding a New Agent

Update `docs/SYSTEM_REGISTRY_FEB04_2026.md`:

```markdown
### Agent Name
- **Type**: specialist/coordinator/worker
- **Module**: `mycosoft_mas/agents/your_agent.py`
- **Capabilities**: [list capabilities]
- **Version**: 1.0.0
```

Or register via API: `POST http://192.168.0.188:8001/api/registry/agents`

## When Adding API Endpoints

Update `docs/API_CATALOG_FEB04_2026.md`:

```markdown
| /api/your-domain/endpoint | METHOD | Description |
```

Or trigger auto-indexing: `POST http://192.168.0.188:8001/api/registry/apis/index`

## When Creating Documentation

Update `docs/MASTER_DOCUMENT_INDEX.md`:

```markdown
| Filename | Description | Date | Category |
```

## Checklist

```
Registry Update Progress:
- [ ] MASTER_DOCUMENT_INDEX.md (if new docs)
- [ ] SYSTEM_REGISTRY (if new agents/services/devices)
- [ ] API_CATALOG (if new endpoints)
- [ ] system_map.md (if architecture changes)
```
