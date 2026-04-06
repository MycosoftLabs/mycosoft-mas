# Nemotron Model Comparison and Decision Dossier (Mar 31, 2026)

Date: Mar 31, 2026  
Status: Draft for architecture decision  
Scope: MYCA/AVANI corporate-first migration from Llama/Ollama to Nemotron-backed routing

## Objective

Select a production-safe Nemotron primary and fallback model stack for MYCA, with explicit trade-offs for:
- context window
- pricing
- latency/throughput
- compatibility with current OpenAI-compatible runtime paths

## Sources

- [OpenRouter NVIDIA model index](https://openrouter.ai/nvidia)
- [OpenRouter Nemotron 3 Super model page](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b)
- [OpenRouter Nemotron 3 Nano 30B A3B model page](https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b)
- [OpenRouter Nemotron Nano 9B v2 model page](https://openrouter.ai/nvidia/nemotron-nano-9b-v2)
- [OpenRouter Nemotron-4 340B model page](https://openrouter.ai/nvidia/nemotron-4-340b-instruct)

## Candidate Models

| Candidate | Context Window | Pricing (Input / Output per 1M) | Notes |
|---|---:|---:|---|
| `nvidia/nemotron-3-super-120b-a12b` | 262K (provider-advertised); vendor page describes 1M-class long context capability | $0.10 / $0.50 (DeepInfra lane on OpenRouter), higher on other lanes | Highest quality candidate for user-facing and reasoning-heavy tasks. |
| `nvidia/nemotron-3-nano-30b-a3b` | 256K-262K (provider-dependent) | $0.05 / $0.20 | Strong cost/performance candidate for edge/infra routing. |
| `nvidia/nemotron-nano-9b-v2` | 128K-131K (provider-dependent) | $0.04 / $0.16 | Lowest-cost small model for fast/simple agent paths. |
| `nvidia/nemotron-4-340b-instruct` | 4K | Provider-dependent | Not suitable for MYCA long-context memory/consciousness paths. |

## Latency and Throughput Snapshot

From OpenRouter live telemetry for Nemotron 3 Super (provider lanes vary over time):
- throughput observed: roughly 98-109 tokens/sec (provider-dependent)
- first-token latency: roughly 1.1-2.8s (provider-dependent)
- end-to-end latency: roughly 6.3-7.5s (provider-dependent)

These values are routing-layer measurements, not direct NIM bare-metal benchmarks. Treat as baseline for migration gating, not hard SLA.

## Compatibility Assessment

### Existing MAS compatibility status

Current MYCA code already supports Nemotron via OpenAI-compatible endpoints:
- `config/models.yaml` has `nemotron` provider and role mappings.
- `mycosoft_mas/llm/backend_selection.py` resolves role-based provider/model.
- `mycosoft_mas/llm/router.py` and `mycosoft_mas/myca/os/llm_brain.py` call OpenAI-compatible chat paths.

### Required compatibility checks before production cutover

- streaming parity for website routes (`/api/chat`, `/api/mas/chat`, test-voice and MYCA routes)
- fallback semantics preserved when Nemotron endpoint errors/timeouts
- response contract shape unchanged for AVANI front-end consumers
- ledger and persistence metadata stable for downstream MINDEX/NLM readers

## Recommendation by Agent Category

### Corporate (user-facing) - Priority 1
- Primary: Nemotron 3 Super
- Fallback: Ollama/Llama (`llama3.2` existing fallback path)
- Rationale: best answer quality and long-context coherence for executive and user-facing conversations.

### Infrastructure
- Primary: Nemotron 3 Nano 30B A3B
- Fallback: Ollama/Llama
- Rationale: lower cost and faster completion while retaining enough reasoning for ops workflows.

### Device
- Primary: Nemotron Nano 9B v2 (or Nemotron 3 Nano where quality requires)
- Fallback: Ollama/Llama
- Rationale: lower latency and cost for command/telemetry interpretation.

### Route / Routing-Function Workflows
- Primary: Nemotron 3 Nano 30B A3B
- Fallback: Ollama/Llama
- Rationale: good trade-off for intent routing and workflow dispatch.

### NLM / Consciousness Paths
- Primary: Nemotron 3 Super for high-context cognitive paths
- Secondary fast lane: Nemotron 3 Nano for low-risk summarization/reduction steps
- Fallback: Ollama/Llama

## Cost and Risk Controls

- enforce per-category token caps and timeout budgets
- start in hybrid mode with hard fallback
- promote only after quality and latency gates pass per category
- keep global rollback flag (`MYCA_BACKEND_MODE=llama`) available at all times

## Decision Needed from Morgan

1. Confirm production endpoint provider (OpenRouter, NIM-hosted endpoint, or other OpenAI-compatible gateway).
2. Confirm final primary model for Corporate and Consciousness paths.
3. Confirm max tolerated p95 latency per category for go/no-go gates.

