.PHONY: dev build test lint format up down clean logs help

dev: ## Start all services in docker development mode (database + backend + frontend)
	docker compose up --build -d
	@echo "✅ Services started."

up: ## Start local infrastructure services (Postgres, Redis, Qdrant)
	docker compose up -d postgres redis qdrant
	@echo "✅ Infrastructure services running."

down: ## Stop all services
	docker compose down

logs: ## Tail all service logs
	docker compose logs -f

test: ## Run backend tests
	cd backend && python -m pytest tests/ -v --tb=short

lint: ## Run Python code linters (ruff, mypy)
	cd backend && python -m ruff check app/
	cd backend && python -m mypy app/ --ignore-missing-imports

format: ## Run Python formatting
	cd backend && python -m ruff format app/

clean: ## Stop services and delete volumes/temporary caches
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "🧹 Volumes and caches cleared."

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
