# Development Guide

HelloSales development workflow and best practices.

## Getting Started

1. **Clone repository**
   ```bash
   git clone <repo-url> HelloSales
   cd HelloSales
   ```

2. **Run setup script**
   ```bash
   ./setup.sh
   ```
   This creates virtual env, installs dependencies, and starts infrastructure.

## Workflow

### Backend Development

```bash
# Terminal 1: Infrastructure
make up

# Terminal 2: Backend
cd backend
./venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 3: Tests (optional)
cd backend
./venv/bin/pytest -xvs tests/ -f  # Watch mode
```

### Mobile Development

```bash
# Terminal: Mobile
cd mobile
npx expo start --port 8002
# Scan QR code or visit http://localhost:8002
```

## Code Style

### Backend (Python)

Follow PEP 8 with Ruff.

**Linting**:
```bash
cd backend
./venv/bin/ruff check .
```

**Formatting**:
```bash
cd backend
./venv/bin/ruff format .
```

**Type Hints**:
- All functions require type hints
- Use `|` for Union types (Python 3.10+)
- Use `dict[str, Any]` for dicts

**Docstrings**:
```python
def my_function(param: str) -> dict[str, Any]:
    """Brief description.

    Args:
        param: Parameter description

    Returns:
        Return value description
    """
    ...
```

### Mobile (TypeScript)

**Linting**:
```bash
cd mobile
npx tsc --noEmit
```

**Component Pattern**:
```typescript
import { View, Text } from 'react-native';
import { Box, Text as UiText } from '../_components/ui';

function MyScreen() {
  return (
    <Box>
      <UiText variant="h3">Title</UiText>
      <Text>Native text</Text>
    </Box>
  );
}
```

**State Pattern**:
```typescript
// Use Zustand stores
import { useClientsStore } from './stores';

function MyScreen() {
  const { clients, setClients } = useClientsStore();

  // Access or update state
}
```

## Testing

### Backend Tests

**Structure**:
```
tests/
├── unit/              # Isolated unit tests
├── integration/       # Integration tests with DB
└── conftest.py       # Shared fixtures
```

**Write Tests**:
```python
# tests/unit/test_example.py
import pytest
from app.models.user import User

def test_user_creation():
    user = User(email="test@example.com")
    assert user.email == "test@example.com"
```

**Run Tests**:
```bash
# All tests
./venv/bin/pytest -xvs tests/

# Unit only
./venv/bin/pytest -xvs tests/unit/

# Integration only
./venv/bin/pytest -xvs tests/integration/

# Specific test
./venv/bin/pytest -xvs tests/integration/test_websocket.py

# Watch mode
./venv/bin/pytest -xvs tests/ -f
```

### Mobile Tests

Currently not configured. Use EAS Test or React Native Testing Library.

## Database Changes

### Create Migration

```bash
cd backend
./venv/bin/alembic revision -m "description"
```

Edit generated migration file in `migrations/versions/`.

### Apply Migration

```bash
./venv/bin/alembic upgrade head
```

### Rollback

```bash
./venv/bin/alembic downgrade -1
```

### Migration Best Practices

1. Write reversible migrations (upgrade and downgrade)
2. Use SQL operations, not ORM, in migrations
3. Test migrations on copy of production DB
4. Include data migration scripts if needed

## Adding Features

### Backend REST Endpoint

1. **Create schema** in `app/schemas/`:
   ```python
   from pydantic import BaseModel

   class MyRequest(BaseModel):
       name: str

   class MyResponse(BaseModel):
       id: str
       name: str
   ```

2. **Create handler** in `app/api/http/`:
   ```python
   from fastapi import APIRouter

   router = APIRouter(prefix="/api/v1/my", tags=["my"])

   @router.get("/")
   async def list_items():
       return [{"id": "1", "name": "Item"}]

   @router.post("/")
   async def create_item(req: MyRequest):
       return {"id": "1", "name": req.name}
   ```

3. **Register router** in `app/main.py`:
   ```python
   from app.api.http.my import router as my_router

   app.include_router(my_router)
   ```

### Backend WebSocket Handler

1. **Create handler** in `app/api/ws/handlers/`:
   ```python
   from app.api.ws.router import router

   @router.handler("my_message")
   async def handle_my_message(websocket, payload, manager):
       # Handle message
       await manager.send_message(websocket, {
           "type": "my_response",
           "payload": {"data": "result"}
       })
   ```

2. **Auto-registered** via decorator

### Mobile Screen

1. **Create screen** in `app/screens/`:
   ```typescript
   import { ScrollScreen, Text, Button } from '../_components/ui';

   export default function MyScreen() {
     return (
       <ScrollScreen>
         <Text variant="h3">My Screen</Text>
         <Button onPress={() => {}}>Action</Button>
       </ScrollScreen>
     );
   }
   ```

2. **Add route** in `app/` (create or edit route file):
   ```typescript
   import { Stack } from 'expo-router';
   import MyScreen from './screens/MyScreen';

   export default function Layout() {
     return (
       <Stack>
         <Stack.Screen name="my" component={MyScreen} />
       </Stack>
     );
   }
   ```

### Mobile API Client

1. **Add method** in `services/api.ts`:
   ```typescript
   export const myApi = {
     listItems: () =>
       api.get<MyResponse[]>('/api/v1/my/items'),

     createItem: (data: MyCreateRequest) =>
       api.post<MyResponse>('/api/v1/my/items', data),
   };
   ```

2. **Consume in component**:
   ```typescript
   import { myApi } from '../../services/api';

   function MyScreen() {
     const loadItems = async () => {
       const items = await myApi.listItems();
       // Use items
     };
   }
   }
   ```

## Debugging

### Backend

**Logging**:
- Structured JSON logs
- Request ID tracking
- Service identification

**View Logs**:
```bash
# Terminal output from uvicorn
tail -f backend.log

# Docker logs
docker compose logs -f db redis
```

**Debug Mode**:
```bash
export LOG_LEVEL=DEBUG
export LOG_DEBUG_NAMESPACES=llm,voice,chat
./venv/bin/uvicorn app.main:app --reload
```

### Mobile

**Debugging**:
- Use Expo DevTools
- React DevTools (web)
- Flipper (native)

**View Logs**:
```bash
# Terminal output from expo
npx expo start

# Device logs
npx expo logcat  # Android
npx expo ios   # iOS
```

## Environment Configuration

### Backend (.env)

```env
# Core
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://hellosales:hellosales_dev@localhost:5434/hellosales
REDIS_URL=redis://localhost:6380/0

# Auth
WORKOS_CLIENT_ID=
WORKOS_API_KEY=

# AI
GROQ_API_KEY=
DEEPGRAM_API_KEY=
GOOGLE_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_DEBUG_NAMESPACES=

# Features
PIPELINE_MODE=fast
ASSESSMENT_ENABLED=false
```

### Mobile (.env)

```bash
EXPO_PUBLIC_API_URL=http://localhost:8000
```

## Git Workflow

### Branch Strategy

```
main          # Production
├── develop  # Integration branch
    ├── feature/add-xyz
    ├── bugfix/issue-123
    └── hotfix/critical-issue
```

### Commit Messages

```
feat: add client archetypes feature
fix: resolve authentication token expiration
docs: update API documentation
refactor: extract auth logic to service
test: add integration tests for WebSocket
chore: update dependencies
```

### Pull Requests

1. Update `CHANGELOG.md` (if applicable)
2. Ensure all tests pass
3. Update documentation
4. Request review from at least one maintainer

## Deployment

### Backend

**Local**:
```bash
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Docker**:
```bash
docker build -t hellosales-backend .
docker run -p 8000:8000 --env-file .env hellosales-backend
```

**Production**:
- Use Gunicorn with Uvicorn workers
- Configure connection pooling
- Set up monitoring
- Use environment-specific secrets

### Mobile

**Development**:
```bash
npx expo start
```

**Production**:
```bash
# iOS
eas build --platform ios

# Android
eas build --platform android

# Web
npm run build:web
```

## Troubleshooting

### Backend Issues

**Port already in use**:
```bash
lsof -i :8000
kill -9 <PID>
```

**Migration errors**:
```bash
# Check current migration
./venv/bin/alembic current

# Stuck migration
./venv/bin/alembic stamp head
```

**Database connection**:
```bash
# Check Docker
docker compose ps
docker compose logs db

# Test connection
make shell-db
SELECT 1;
```

### Mobile Issues

**Metro bundler issues**:
```bash
# Clear cache
npx expo start -c
rm -rf node_modules
npm install
```

**iOS build fails**:
```bash
# Clean pods
cd ios && pod install
```

## Resources

- **Backend**: `backend/README.md`
- **Mobile**: `mobile/README.md`
- **Architecture**: `ARCHITECTURE.md`
- **API**: `API.md`
