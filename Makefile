COMPOSE ?= docker compose
PROFILE ?=
PROFILE_FLAG := $(if $(PROFILE),--profile $(PROFILE),)

.PHONY: up up-llm observability down logs ps build test fmt reset-db help ingest-myceliumseg validate-sim

up:
	$(COMPOSE) $(PROFILE_FLAG) up -d

up-llm:
	$(COMPOSE) --profile local-llm up -d

observability:
	$(COMPOSE) --profile observability up -d

down:
	$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE) $(PROFILE_FLAG) logs -f --tail=200

ps:
	$(COMPOSE) $(PROFILE_FLAG) ps

build:
	$(COMPOSE) $(PROFILE_FLAG) build

test:
	poetry run pytest

fmt:
	poetry run black .
	poetry run isort .

reset-db:
	$(COMPOSE) stop postgres || true
	$(COMPOSE) rm -f postgres || true
	$(COMPOSE) down --volumes --remove-orphans

# MyceliumSeg (Phase 0): apply migration 021 then run ingest; requires MINDEX_DATABASE_URL
ingest-myceliumseg:
	python scripts/ingest_myceliumseg.py --fixture

# MyceliumSeg: run validation job; pass slice via SLICE env e.g. SLICE='{"species":["GL"],"limit":5}'
validate-sim:
	@echo "Submit a job via POST /mindex/myceliumseg/validation/jobs then run: python scripts/myceliumseg/run_validation_job.py <job_id>"

help:
	@echo "Targets:"
	@echo "  up            - start stack (set PROFILE=observability or local-llm)"
	@echo "  up-llm        - start stack with local LLM profile"
	@echo "  observability - start observability profile (Prometheus/Grafana)"
	@echo "  down          - stop stack"
	@echo "  logs          - follow logs"
	@echo "  ps            - show status"
	@echo "  build         - build images"
	@echo "  test          - run pytest"
	@echo "  fmt           - format with black + isort"
	@echo "  reset-db      - reset postgres volume (destructive)"
	@echo "  ingest-myceliumseg - ingest MyceliumSeg fixture (set MINDEX_DATABASE_URL)"
	@echo "  validate-sim  - see MyceliumSeg validation instructions"