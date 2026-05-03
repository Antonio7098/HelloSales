# Backend Scripts

This directory contains development and build scripts for the HelloSales backend.

## Scripts

| Script | Purpose |
|---|---|
| [smoke.py](smoke.py) | Smoke test runner for scaffold validation |
| [verify_postgres.py](verify_postgres.py) | Database connectivity verification |
| [scaffold_module.py](scaffold_module.py) | Generate new bounded-context modules |

## Usage

### Smoke Tests
```bash
python3 scripts/smoke.py                    # Run all smoke suites
python3 scripts/smoke.py --list           # List available suites
python3 scripts/smoke.py generic-agent-provider  # Run specific suite
```

### Database Verification
```bash
python3 scripts/verify_postgres.py
```

### Module Scaffolding
```bash
python3 scripts/scaffold_module.py deals
```

Or after installing the package:
```bash
hello-sales-scaffold-module deals
```

## Requirements

- Python 3.12+
- PostgreSQL (for verify_postgres.py)
- Dependencies from `pyproject.toml`