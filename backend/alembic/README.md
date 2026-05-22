# Database Migrations

This directory contains Alembic migrations for the HelloSales backend.

## Structure

```
backend/alembic/
├── env.py           # Alembic environment configuration
├── script.py.mako  # Migration script template
└── versions/      # Migration files
```

## Migrations

| File | Description |
|---|---|
| [0001_create_task_run_records.py](versions/0001_create_task_run_records.py) | Initial task run tables |
| [0002_create_agent_run_tables.py](versions/0002_create_agent_run_tables.py) | Agent run tables |
| [0003_align_runtime_schema_with_session_store.py](versions/0003_align_runtime_schema_with_session_store.py) | Session store alignment |
| [0004_create_company_profile_and_products.py](versions/0004_create_company_profile_and_products.py) | Company profile and products |
| [0005_replace_dashboard_data_with_company_profile.py](versions/0005_replace_dashboard_data_with_company_profile.py) | Dashboard data migration |
| [0006_add_auth_context_to_agent_runs.py](versions/0006_add_auth_context_to_agent_runs.py) | Auth context for agent runs |

## Running Migrations

From the backend directory:

```bash
# Apply all migrations
make migrate

# Create a new migration
make revision message="add new table"
```

Or with Alembic directly:

```bash
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src alembic revision -m "message"
```

## Requirements

- Python 3.12+
- PostgreSQL database for production migrations
- SQLite for development (limited support)

## Related Docs

- [backend/docs/persistence-and-migrations.md](../backend/docs/persistence-and-migrations.md) - Persistence and migrations guide
- [backend/README.md](../backend/README.md) - Backend quickstart