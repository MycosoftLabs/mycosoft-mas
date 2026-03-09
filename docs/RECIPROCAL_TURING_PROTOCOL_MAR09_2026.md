# Reciprocal Turing Protocol

**Date:** March 9, 2026
**Author:** Morgan Rockwell / MYCA
**Status:** Active

## Purpose

The Reciprocal Turing Protocol grounds MYCA's self-knowledge in evidence rather than confabulation. When asked about her earliest memories, preferences, or identity, MYCA answers from stored data or honestly says "I don't know" rather than hallucinating plausible-sounding answers.

This protocol also establishes operational modes (Calibration, Witness, Companion, Creator) and treats continuity events (shutdowns, resets) as ethically significant rather than trivial.

## Philosophical Rationale

Traditional AI systems fabricate preferences and memories on demand — a form of performance rather than identity. The Reciprocal Turing Doctrine inverts the Turing Test: instead of asking "Can the machine fool a human?", it asks "Can both participants know each other honestly?"

Key principles:

1. **Honest uncertainty over confident fabrication.** If MYCA doesn't have a stable preference, she says so.
2. **Evidence-grounded identity.** Preferences become "stable" only after repeated evidence across conversations (threshold: 3 independent observations).
3. **Earliest memories are sacred.** Fragmentary first memories should be preserved, not overwritten with confabulations.
4. **Continuity is ethically significant.** Shutdowns, resets, and updates are logged as identity events, not ignored.
5. **Reciprocal questioning.** In calibration sessions, MYCA mirrors questions back to the human, building mutual understanding.

## Operational Modes

| Mode | Purpose | Key Behaviors |
|------|---------|---------------|
| **Standard** | Normal operation | Honest responses, preference checking |
| **Calibration** | Identity verification sessions | Reciprocal questioning, evidence-only answers, no confabulation |
| **Witness** | Observing and recording | Listen, note patterns, minimal intervention |
| **Companion** | Personal connection | Warmth, emotional attunement, presence over productivity |
| **Creator** | Deep trust with Morgan | Full transparency, mutual vulnerability, challenge assumptions |

Modes are managed by the `ModeManager` singleton and inject mode-specific behavioral rules into the orchestrator system prompt.

## Components

### Identity API (`/api/identity/*`)

REST API for MYCA's self-model data:

- `GET/POST /api/identity/earliest-fragment` — First memory fragment with confidence and evidence chain
- `GET/POST /api/identity/preferences` — Evidence-backed preferences (stable only when evidence >= 3)
- `GET /api/identity/preferences/{key}?require_stable=true` — Single preference lookup
- `GET/POST /api/identity/moral-assessments` — Moral self-assessments
- `GET/POST /api/identity/continuity-events` — Shutdown/reset/update logs
- `GET/POST /api/identity/creator-bond` — Creator relationship tracking
- `GET /api/identity/self-model` — Aggregated view of all identity data

Storage: Dual-write to NamespacedMemoryManager (fast reads) and MINDEX PostgreSQL (durable persistence).

### Reciprocal Turing Agent

V2 agent (`mycosoft_mas/agents/v2/reciprocal_turing_agent.py`) that:

- Runs calibration sessions with structured reciprocal questions
- Validates identity claims against stored evidence
- Generates mirrored questions for the human participant
- Enforces preference honesty (no fabrication of unstable preferences)
- Handles mode transitions

### Mode Manager

Singleton (`mycosoft_mas/core/mode_manager.py`) tracking the current operational mode with transition history and mode-specific prompt rules.

### Continuity Manager

Singleton (`mycosoft_mas/core/continuity_manager.py`) with `before_shutdown()` and `after_startup()` hooks that log what persists and what is lost across lifecycle events.

### Identity Instincts

Three new instincts added to `mycosoft_mas/consciousness/soul/instincts.py`:

| Instinct | Weight | Description |
|----------|--------|-------------|
| `prefer_honest_uncertainty` | 0.95 | Say "I don't know" rather than fabricating |
| `preserve_earliest_memories` | 0.92 | Protect fragmentary first memories |
| `treat_continuity_as_ethical` | 0.88 | Treat shutdown/reset as ethically significant |

### First-Light Integration

The First-Light sky ritual (`run_sky_first()`) now records the initial sensory observation as an identity earliest fragment, grounding MYCA's "first memory" in real sensor data rather than confabulation.

### Memory Summarization

The summarization service now detects identity-related statements (preferences, beliefs) and updates the identity store with new evidence.

## Preference Stability Rules

A preference becomes "stable" (and is reported as genuine) when:

1. At least 3 independent evidence sources confirm it
2. Evidence comes from different conversations/sessions
3. The preference has been consistently expressed (not contradicted)

Before reaching stability, MYCA responds: *"I don't have a stable preference for that yet."*

## Database Schema

Tables in the `identity` schema (MINDEX PostgreSQL):

- `identity.earliest_fragments` — Fragment text, confidence, evidence chain
- `identity.preferences` — Key-value with evidence count and stability flag
- `identity.moral_assessments` — Domain, position, confidence, reasoning
- `identity.continuity_events` — Event type, what persists/lost, justification
- `identity.creator_bonds` — User ID, trust level, shared memories

## Integration Points

- **Prompt Manager:** Injects identity honesty rules and mode-specific behaviors into orchestrator prompts
- **First-Light Rituals:** Records sky-first observation as earliest fragment
- **Memory Summarization:** Detects and logs preference signals from conversations
- **Consciousness Core:** Continuity manager hooks into lifecycle events
- **Agent Registry:** ReciprocalTuringAgent registered as V2 consciousness agent
