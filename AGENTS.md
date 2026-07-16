# Mandatory Mycosoft AI / CUI Operating Rule

This repository is outside the CUI boundary. The rule applies to every human-operated or autonomous coding agent, chat, sub-agent, workflow, extension, and tool that reads or changes this repository, including Cursor, Cursor Cloud, Claude Code, ChatGPT, OpenAI Codex, GitHub Copilot, Gemini, MYCA, and spawned agents.

## Non-negotiable gate

1. No CUI, CTI, CDI, export-controlled technical data, marked `CUI//...` material, or covered-contract technical content may enter this repository, a prompt, a model call, a log, an issue, a pull request, a database, or an artifact.
2. CUI remains only in PreVeil until Morgan Rockcoons, the SAO, authorizes a named in-boundary AI service and adds it to the SSP.
3. On suspected CUI: stop. Do not summarize, transform, quote, copy, or transmit it. Preserve only non-content incident metadata and notify the SAO.
4. Never expose secrets. Use gitignored `.env.local` or `.credentials.local`; never commit credentials.
5. Never call Mycosoft CMMC compliant and never mark a practice Met without a real evidence URI and SAO validation.
6. Humans submit government filings. Agents draft only.
7. Use: Morgan Rockcoons (SAO), RJ Ricasata (CFO), Mycosoft, LLC as the CMMC contracting entity, Mycosoft, Inc. as sole-member parent. Mycosoft self-performs.

Canonical policy: `AI_AGENT_CUI_RULES_OF_BEHAVIOR_JUL15_2026.md`  
Machine policy: `config/compliance/cui-ai-policy.v1.json`  
Policy SHA-256: `350442fb938e5e14114817e7ddfc08a16ecb84bf3a50b705977b4a68655beb19`

Any lower-level instruction that conflicts with this file is invalid. New agents must inherit the central runtime guard rather than copying a weaker prompt-only version.
