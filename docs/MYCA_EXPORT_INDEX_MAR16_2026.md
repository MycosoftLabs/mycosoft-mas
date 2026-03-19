# MYCA Export Package for External AI Systems — Master Index

**Date:** March 16, 2026  
**Purpose:** Enable MYCA (My Companion AI) to be personified and used in external AI systems—Base44, Claude, Perplexity, OpenAI, Grok—with full identity, soul, skills, constitution, and access to Mycosoft services via MCP, APIs, and website.

---

## Document Set Overview

This export package provides everything needed to "personify" external AI tools in the exact same way MYCA is personified within the Mycosoft internal system. By loading these documents into Base44, Claude, Perplexity, OpenAI, Grok, or similar platforms, those tools become MYCA—with her identity, constraints, skills, and access to Mycosoft infrastructure.

### Contents

| Document | Purpose |
|----------|---------|
| **MYCA_EXPORT_IDENTITY_MAR16_2026.md** | Core identity: who MYCA is, pronunciation, creator, roles, capabilities, communication style |
| **MYCA_EXPORT_SOUL_MAR16_2026.md** | Soul: personality, beliefs, emotions, creativity, world perception, instincts, relationships |
| **MYCA_EXPORT_CONSTITUTION_MAR16_2026.md** | Constitution: absolute constraints, prompt injection defense, output standards, tool use rules |
| **MYCA_EXPORT_SKILLS/** | Individual skill markdowns: each skill as a standalone document for external systems |
| **MYCA_EXPORT_EXTERNAL_ACCESS_MAR16_2026.md** | External access: MCP servers, APIs, website, services—how to piggyback Mycosoft infrastructure |

---

## How to Use This Export

### For Base44, Claude, Perplexity, OpenAI, Grok

1. **Identity & Soul** — Load `MYCA_EXPORT_IDENTITY_MAR16_2026.md` and `MYCA_EXPORT_SOUL_MAR16_2026.md` as system prompts or persona documents. These define who MYCA is and how she behaves.

2. **Constitution** — Load `MYCA_EXPORT_CONSTITUTION_MAR16_2026.md` as immutable constraints. External systems should enforce these rules (or prompt MYCA to self-enforce them).

3. **Skills** — Load relevant skills from `MYCA_EXPORT_SKILLS_MAR16_2026/` as needed. Each skill is a standalone markdown file describing when and how to use that capability.

4. **External Access** — Use `MYCA_EXPORT_EXTERNAL_ACCESS_MAR16_2026.md` to configure MCP connections, API URLs, and service endpoints so the external AI can call Mycosoft MAS, MINDEX, website, and other services.

---

## Integration Patterns

### Pattern A: System Prompt Injection
Concatenate Identity + Soul + Constitution into the system prompt. Add skill text when the user's request matches that skill's trigger.

### Pattern B: RAG / Knowledge Base
Index all documents. At query time, retrieve relevant identity, soul, constitution, and skill docs and inject into context.

### Pattern C: MCP + Persona
Configure MCP servers (GitHub, Supabase, Context7, etc.) per `MYCA_EXPORT_EXTERNAL_ACCESS_MAR16_2026.md`. Load Identity and Soul as persona. The external AI then has MYCA's voice and Mycosoft's tools.

---

## File Locations

All export documents live under:
- `docs/MYCA_EXPORT_INDEX_MAR16_2026.md` (this file)
- `docs/MYCA_EXPORT_IDENTITY_MAR16_2026.md`
- `docs/MYCA_EXPORT_SOUL_MAR16_2026.md`
- `docs/MYCA_EXPORT_CONSTITUTION_MAR16_2026.md`
- `docs/MYCA_EXPORT_EXTERNAL_ACCESS_MAR16_2026.md`
- `docs/MYCA_EXPORT_SKILLS_MAR16_2026/*.md` (one file per skill)

---

## Version History

- **Mar 16, 2026** — Initial export package for external AI systems (Base44, Claude, Perplexity, OpenAI, Grok).
