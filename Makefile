.PHONY: dev-up dev-down dev-logs dev-ps

COMPOSE := docker compose -f docker-compose.dev.yml

dev-up:
	$(COMPOSE) up -d --build

dev-down:
	$(COMPOSE) down

dev-logs:
	$(COMPOSE) logs -f

dev-ps:
	$(COMPOSE) ps
