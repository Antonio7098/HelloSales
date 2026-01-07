.PHONY: help dev up down restart clean install-backend install-mobile backend mobile test-backend lint-backend format-backend migrate-db shell-db

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: up install-backend install-mobile  ## Start development environment

up:  ## Start infrastructure (PostgreSQL, Redis)
	docker compose up -d

down:  ## Stop infrastructure
	docker compose down

restart:  ## Restart infrastructure
	docker compose restart

clean: down  ## Stop and remove containers, volumes
	docker compose down -v

install-backend:  ## Install backend dependencies
	cd backend && python3 -m venv venv && ./venv/bin/pip install -e ".[dev]"

install-mobile:  ## Install mobile dependencies
	cd mobile && npm install

backend:  ## Start backend server
	cd backend && ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

mobile:  ## Start mobile development server
	cd mobile && npx expo start --port 8002

test-backend:  ## Run backend tests
	cd backend && ./venv/bin/pytest -xvs tests/

lint-backend:  ## Run backend linting
	cd backend && ./venv/bin/ruff check .

format-backend:  ## Run backend formatting
	cd backend && ./venv/bin/ruff format .

migrate-db:  ## Run database migrations
	cd backend && ./venv/bin/alembic upgrade head

shell-db:  ## Open database shell (psql)
	docker exec -it hellosales-db psql -U hellosales -d hellosales

logs-backend:  ## Show backend container logs
	docker compose logs -f db redis

logs-infra:  ## Show infrastructure logs
	docker compose logs -f
