# GitHub Actions CI/CD

This directory contains the GitHub Actions workflows for HelloSales.

## Workflows

### backend-ci.yml

Backend continuous integration pipeline.

**Triggers:** Push to `main`, PRs affecting backend/, and backend-related paths.

**Jobs:**
- **Lint** - Ruff linting
- **Typecheck** - MyPy type checking
- **Test** - Unit tests with SQLite
- **Integration** - PostgreSQL-backed integration tests

**Runners:** ubuntu-latest

---

### frontend-ci.yml

Frontend continuous integration pipeline.

**Triggers:** Push to `main`, PRs affecting frontend/ and frontend-draft/.

**Jobs:**
- **Lint** - ESLint
- **Typecheck** - TypeScript checking
- **Test** - Vitest unit tests
- **Build** - Production build verification

**Runners:** ubuntu-latest

---

## Related Docs

- [../README.md](../README.md) - Project overview
- [backend/README.md](../backend/README.md) - Backend quickstart
- [frontend/README.md](../frontend/README.md) - Frontend quickstart