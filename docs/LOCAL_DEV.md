## Local Development (Docker first)

1) Prereqs
- Docker Desktop/Engine
- Poetry + Python 3.11
- Node.js 20+ (for Next.js UI)

2) Environment
- Copy `env.local.example.txt` to `.env` (or export the vars directly).
- Required keys: `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `LLM_DEFAULT_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY` (or `OPENAI_API_KEY` / `GEMINI_API_KEY`), `APPROVAL_REQUIRED`, `JSON_LOGS`.

3) One-command up
```bash
make up
# add profiles
make up PROFILE=observability   # Prometheus + Grafana
make up-llm                     # LiteLLM + optional Ollama
```

4) Verify
- API: `curl http://localhost:8001/health`
- Ready: `curl http://localhost:8001/ready`
- Metrics: `http://localhost:8001/metrics`
- UI: `http://localhost:3001`
- Prometheus: `http://localhost:9090` (observability profile)
- Grafana: `http://localhost:3000` (observability profile, password from env)
- LiteLLM (local profile): `curl http://localhost:4000/v1/models`

5) LLM routing
- Configure models in `config/models.yaml`.
- Env overrides: `LLM_DEFAULT_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL_*`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `AZURE_OPENAI_API_KEY`.
- Local-first: start `make up-llm` and set `LLM_BASE_URL=http://litellm:4000`.

6) Health and stability
- `/ready` waits for Postgres, Redis, Qdrant.
- JSON logs are on by default (`JSON_LOGS=true`), with request IDs.
- Metrics include HTTP + LLM + tool action counters.

7) Testing & lint
```bash
poetry install --with dev
make test
make fmt
```

8) Reset (destructive)
```bash
make reset-db
```
