# SaleWind Mobile - Backend Connection Guide

This document describes how to connect salewind-mobile to enterprise-backend.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    salewind-mobile (Expo/React Native)      │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Screens   │  │   Stores    │  │    Services/API     │  │
│  │             │  │  (Zustand)  │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │              │
│         └────────────────┴─────────────────────┘              │
│                          │                                   │
│                    @services/api.ts                          │
│         ┌───────────────────────────────┐                    │
│         │       API Client Layer        │                    │
│         └───────────────┬───────────────┘                    │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              enterprise-backend (FastAPI)                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    /api/v1/sailwind                    │  │
│  │                                                       │  │
│  │   clients, products, strategies, rep-assignments,     │  │
│  │   practice-sessions, archetypes                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### 1. Backend (enterprise-backend)

The backend is already configured with CORS for development:

- In development mode: `http://localhost:*` and `http://127.0.0.1:*` are allowed
- Default port: `8000`

### 2. Mobile (salewind-mobile)

Set the API URL in your environment:

```bash
# .env file in salewind-mobile/
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_USE_API=true  # Set to 'true' to use real API, 'false' for mock data
```

Or configure in `app.config.ts`:

```typescript
export default {
  expo: {
    extra: {
      apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
    },
  },
};
```

## Running the Services

### 1. Start the Backend

```bash
cd /home/antonio/programming/eloquence-ui-tweaks/enterprise-backend
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or via Makefile if available
make run
```

### 2. Start the Mobile App

```bash
cd /home/antonio/programming/eloquence-ui-tweaks/salewind-mobile
npm start
# or
npx expo start --port 8002
```

The mobile app runs on port 8002 to avoid conflict with the backend.

## API Endpoints

The following endpoints are available at `/api/v1/sailwind/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/clients` | List all clients |
| POST | `/clients` | Create a client (admin only) |
| PATCH | `/clients/{id}` | Update a client (admin only) |
| GET | `/products` | List all products |
| POST | `/products` | Create a product (admin only) |
| PATCH | `/products/{id}` | Update a product (admin only) |
| GET | `/strategies` | List all strategies |
| POST | `/strategies` | Create a strategy (admin only) |
| GET | `/my/rep-assignments` | Get current user's rep assignments |
| GET | `/my/practice-sessions` | Get current user's practice sessions |
| POST | `/practice-sessions` | Start a new practice session |

## Development Modes

### Mock Mode (Default)

When `EXPO_USE_API` is not set or is `'false'`, the app uses mock data from `data/mockData.ts`. This is useful for UI development without a running backend.

### API Mode

Set `EXPO_USE_API=true` to use the real backend API. The app will:
1. Fetch data from the configured API endpoint
2. Convert API responses to UI models using adapters in `services/adapters.ts`
3. Fall back to mock data if the API is unavailable

## File Structure

```
salewind-mobile/
├── services/
│   ├── api.ts         # API client and endpoint definitions
│   ├── adapters.ts    # Type adapters (API <-> UI models)
│   └── index.ts       # Exports
├── app/
│   ├── stores/
│   │   └── index.ts   # Zustand stores with API integration
│   └── screens/       # UI screens (unchanged)
└── data/
    └── mockData.ts    # Mock data (fallback)
```

## Adding New Endpoints

1. Add the endpoint to `services/api.ts`:
```typescript
export const sailwindApi = {
  // ...existing endpoints
  myNewEndpoint: () => api.get<NewResponse[]>('/api/v1/sailwind/my/new'),
};
```

2. Add adapter in `services/adapters.ts`:
```typescript
export function adaptNewResponse(apiResponse: ApiResponse): UiModel {
  return { /* ... */ };
}
```

3. Update the appropriate store in `app/stores/index.ts`

## Troubleshooting

### CORS Errors

If you see CORS errors:
1. Ensure backend is running in development mode (`is_development=true`)
2. Verify `EXPO_PUBLIC_API_URL` is set correctly in mobile app
3. Check that backend allows the mobile app's port (8002)

### Connection Refused

1. Verify backend is running on the correct port
2. Check firewall settings
3. Use `curl http://localhost:8000/health` to test backend directly

### Type Mismatches

If types don't match between API and UI:
1. Update the adapter in `services/adapters.ts`
2. The backend schemas may need additional fields added
