# [Agent Name] Memory

**Date:** February 17, 2026
**Version:** 1.0.0

## Memory Architecture

This agent uses the following memory layers:

| Layer | Purpose | Retention |
|-------|---------|-----------|
| Session | Current task context | Session duration |
| Short-term | Recent interactions | 24 hours |
| Long-term | Learned patterns | Permanent |
| Semantic | Knowledge graph | Permanent |
| Episodic | Past experiences | 30 days |
| Procedural | How-to knowledge | Permanent |

## Memory Access

### Read Patterns
- What this agent typically reads from memory
- Query patterns and namespaces

### Write Patterns
- What this agent stores in memory
- Update frequency and triggers

## Memory Namespaces

| Namespace | Description | Access |
|-----------|-------------|--------|
| `agent_name:state` | Current agent state | read/write |
| `agent_name:history` | Task history | read/write |
| `shared:knowledge` | Shared knowledge base | read |

## Memory Hygiene

### Cleanup Rules
- Remove stale entries after X days
- Compact duplicates weekly
- Archive completed tasks

### Privacy Rules
- Never store secrets in memory
- Pseudonymize user data
- Hash sensitive arguments

## Integration

This agent's memory integrates with:
- `mycosoft_mas/memory/coordinator.py` - Central memory hub
- `mycosoft_mas/memory/vector_memory.py` - Semantic search
- MINDEX API - Long-term storage
