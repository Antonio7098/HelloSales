.PHONY: dev-db-up dev-db-down dev-db-logs verify-db migrate revision test test-postgres mypy smoke smoke-provider-agent smoke-provider-baseline smoke-provider-observer smoke-provider-append smoke-provider-approval smoke-provider-events smoke-provider-worker scaffold-module

dev-db-up:
	docker compose -f docker-compose.dev.yml up -d postgres

dev-db-down:
	docker compose -f docker-compose.dev.yml down

dev-db-logs:
	docker compose -f docker-compose.dev.yml logs -f postgres

verify-db:
	python3 scripts/verify_postgres.py

migrate:
	alembic upgrade head

revision:
	@test -n "$(message)" || (echo "Usage: make revision message='create table'" && exit 1)
	alembic revision -m "$(message)"

test:
	python3 -m pytest tests -q

test-postgres:
	HELLO_SALES_RUN_POSTGRES_TESTS=1 python3 -m pytest tests/postgres -q

mypy:
	python3 -m mypy src

smoke-provider-agent:
	python3 scripts/smoke.py generic-agent-provider

smoke:
	python3 scripts/smoke.py generic-agent-provider

smoke-provider-baseline:
	python3 scripts/smoke.py generic-agent-provider-baseline

smoke-provider-observer:
	python3 scripts/smoke.py observer-agent-provider

smoke-provider-append:
	python3 scripts/smoke.py generic-agent-provider-append-turn

smoke-provider-approval:
	python3 scripts/smoke.py generic-agent-provider-approval-boundary

smoke-provider-events:
	python3 scripts/smoke.py generic-agent-provider-event-stream

smoke-provider-worker:
	python3 scripts/smoke.py worker-provider-baseline

scaffold-module:
	@test -n "$(name)" || (echo "Usage: make scaffold-module name=deals" && exit 1)
	python3 scripts/scaffold_module.py $(name)
