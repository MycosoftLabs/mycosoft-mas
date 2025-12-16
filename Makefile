# Mycosoft MAS - Development Makefile
# =====================================
# Run `make help` for available commands

.PHONY: help up down logs test fmt lint reset-db clean build shell db-shell redis-cli ps health ready

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RESET := \033[0m

# Docker compose command
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml

# Service names
SERVICES := mas-orchestrator postgres redis qdrant prometheus grafana litellm

help: ## Show this help message
	@echo "$(CYAN)Mycosoft MAS - Development Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make up          # Start all services"
	@echo "  make up-local    # Start with local LLM profile"
	@echo "  make logs        # Tail all logs"
	@echo "  make logs s=mas-orchestrator  # Tail specific service"

# ============================================================================
# Docker Compose Commands
# ============================================================================

up: ## Start all services (MAS + dependencies)
	$(COMPOSE) -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✓ Services started. Run 'make health' to check status.$(RESET)"

up-build: ## Start all services with rebuild
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)✓ Services rebuilt and started.$(RESET)"

up-local: ## Start with local LLM profile (Ollama + LiteLLM)
	$(COMPOSE) -f $(COMPOSE_FILE) --profile local-llm up -d
	@echo "$(GREEN)✓ Services started with local LLM.$(RESET)"

up-observability: ## Start with full observability stack
	$(COMPOSE) -f $(COMPOSE_FILE) --profile observability up -d
	@echo "$(GREEN)✓ Services started with observability.$(RESET)"

down: ## Stop all services
	$(COMPOSE) -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✓ Services stopped.$(RESET)"

down-v: ## Stop all services and remove volumes
	$(COMPOSE) -f $(COMPOSE_FILE) down -v
	@echo "$(YELLOW)⚠ Services stopped and volumes removed.$(RESET)"

restart: down up ## Restart all services

ps: ## Show running services
	$(COMPOSE) -f $(COMPOSE_FILE) ps

logs: ## Tail logs (use s=<service> for specific service)
ifdef s
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(s)
else
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f
endif

# ============================================================================
# Health & Status
# ============================================================================

health: ## Check health endpoint
	@echo "$(CYAN)Checking health...$(RESET)"
	@curl -sf http://localhost:8001/health | python -m json.tool 2>/dev/null || echo "$(YELLOW)Service not ready yet$(RESET)"

ready: ## Check readiness endpoint
	@echo "$(CYAN)Checking readiness...$(RESET)"
	@curl -sf http://localhost:8001/ready | python -m json.tool 2>/dev/null || echo "$(YELLOW)Service not ready yet$(RESET)"

wait: ## Wait for services to be ready
	@echo "$(CYAN)Waiting for services...$(RESET)"
	@timeout 60 bash -c 'until curl -sf http://localhost:8001/ready > /dev/null 2>&1; do echo "Waiting..."; sleep 2; done'
	@echo "$(GREEN)✓ Services ready!$(RESET)"

# ============================================================================
# Development
# ============================================================================

build: ## Build Docker images
	$(COMPOSE) -f $(COMPOSE_FILE) build

fmt: ## Format Python code
	@echo "$(CYAN)Formatting code...$(RESET)"
	poetry run black mycosoft_mas tests
	poetry run isort mycosoft_mas tests
	@echo "$(GREEN)✓ Code formatted.$(RESET)"

lint: ## Run linters
	@echo "$(CYAN)Running linters...$(RESET)"
	poetry run black --check mycosoft_mas tests
	poetry run isort --check mycosoft_mas tests
	poetry run mypy mycosoft_mas
	poetry run pylint mycosoft_mas
	@echo "$(GREEN)✓ Lint checks passed.$(RESET)"

test: ## Run tests
	@echo "$(CYAN)Running tests...$(RESET)"
	poetry run pytest tests/ -v
	@echo "$(GREEN)✓ Tests completed.$(RESET)"

test-cov: ## Run tests with coverage
	poetry run pytest tests/ -v --cov=mycosoft_mas --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(RESET)"

test-smoke: ## Run smoke tests against running services
	@echo "$(CYAN)Running smoke tests...$(RESET)"
	@curl -sf http://localhost:8001/health > /dev/null && echo "$(GREEN)✓ Health check passed$(RESET)" || echo "$(YELLOW)✗ Health check failed$(RESET)"
	@curl -sf http://localhost:8001/ready > /dev/null && echo "$(GREEN)✓ Ready check passed$(RESET)" || echo "$(YELLOW)✗ Ready check failed$(RESET)"
	@curl -sf http://localhost:8001/metrics > /dev/null && echo "$(GREEN)✓ Metrics endpoint available$(RESET)" || echo "$(YELLOW)✗ Metrics unavailable$(RESET)"

# ============================================================================
# Database
# ============================================================================

reset-db: ## Reset database (WARNING: destroys all data)
	@echo "$(YELLOW)⚠ This will destroy all database data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(COMPOSE) -f $(COMPOSE_FILE) stop postgres
	$(COMPOSE) -f $(COMPOSE_FILE) rm -f postgres
	docker volume rm $$(docker volume ls -q | grep postgres_data) 2>/dev/null || true
	$(COMPOSE) -f $(COMPOSE_FILE) up -d postgres
	@echo "$(GREEN)✓ Database reset.$(RESET)"

db-shell: ## Open PostgreSQL shell
	$(COMPOSE) -f $(COMPOSE_FILE) exec postgres psql -U mas -d mas

migrate: ## Run database migrations
	@echo "$(CYAN)Running migrations...$(RESET)"
	$(COMPOSE) -f $(COMPOSE_FILE) exec mas-orchestrator python -m mycosoft_mas.scripts.migrate
	@echo "$(GREEN)✓ Migrations completed.$(RESET)"

# ============================================================================
# Utilities
# ============================================================================

shell: ## Open shell in MAS container
	$(COMPOSE) -f $(COMPOSE_FILE) exec mas-orchestrator /bin/bash

redis-cli: ## Open Redis CLI
	$(COMPOSE) -f $(COMPOSE_FILE) exec redis redis-cli

clean: ## Clean up Docker resources
	@echo "$(CYAN)Cleaning up...$(RESET)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)✓ Cleaned up.$(RESET)"

# ============================================================================
# LLM Configuration
# ============================================================================

llm-test: ## Test LLM connection
	@echo "$(CYAN)Testing LLM connection...$(RESET)"
	@curl -sf http://localhost:4000/health | python -m json.tool 2>/dev/null || echo "$(YELLOW)LiteLLM not running$(RESET)"

llm-models: ## List available LLM models
	@echo "$(CYAN)Available models:$(RESET)"
	@curl -sf http://localhost:4000/v1/models | python -m json.tool 2>/dev/null || echo "$(YELLOW)LiteLLM not running$(RESET)"

# ============================================================================
# Monitoring
# ============================================================================

grafana-open: ## Open Grafana in browser
	@echo "$(CYAN)Opening Grafana (admin/admin)...$(RESET)"
	@start http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null

prometheus-open: ## Open Prometheus in browser
	@start http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null
