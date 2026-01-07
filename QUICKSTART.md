# HelloSales

## Getting Started

1. Start infrastructure:
   ```bash
   make up
   ```

2. Install dependencies:
   ```bash
   make install-backend
   make install-mobile
   ```

3. Configure environment:
   ```bash
   cd backend && cp .env.example .env
   # Edit .env with your API keys
   ```

4. Run migrations:
   ```bash
   make migrate-db
   ```

5. Start services:
   ```bash
   # Backend (terminal 1)
   make backend

   # Mobile (terminal 2)
   make mobile
   ```

## Development

- Backend API docs: http://localhost:8000/docs
- Mobile: Scan Expo QR code with Expo Go app

## Common Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make up` | Start infrastructure (Postgres, Redis) |
| `make down` | Stop infrastructure |
| `make backend` | Start backend server |
| `make mobile` | Start mobile development server |
| `make test-backend` | Run backend tests |
| `make lint-backend` | Run backend linting |
| `make migrate-db` | Run database migrations |
| `make shell-db` | Open database shell |
| `make logs` | View infrastructure logs |

## Documentation

- [Backend README](backend/README.md)
- [Mobile README](mobile/README.md)
