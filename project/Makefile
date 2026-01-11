.PHONY: help install dev test lint format run migrate docker-up docker-down clean

# Default target
help:
	@echo "HelloSales Backend Development Commands"
	@echo ""
	@echo "  make install      - Install dependencies with uv"
	@echo "  make dev          - Run development server with hot reload"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code"
	@echo "  make run          - Run production server"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-new  - Create a new migration"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make clean        - Remove cache files"
	@echo ""

# Install dependencies
install:
	uv venv
	uv pip install -e ".[dev]"

# Run development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

# Linting
lint:
	ruff check app tests
	ruff format --check app tests

# Format code
format:
	ruff check --fix app tests
	ruff format app tests

# Run production server
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Database migrations
migrate:
	alembic upgrade head

migrate-new:
	@read -p "Migration name: " name; \
	alembic revision --autogenerate -m "$$name"

migrate-down:
	alembic downgrade -1

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ dist/ build/ *.egg-info/ 2>/dev/null || true

# Type checking
typecheck:
	pyright app

# Generate OpenAPI schema
openapi:
	python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
