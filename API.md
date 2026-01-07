# HelloSales API Documentation

REST and WebSocket API reference.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: Configured via environment

## Authentication

All API requests require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <workos_jwt>
```

### Development Mode

For local development, use the literal token `"dev_token"` instead of a real JWT.

## REST Endpoints

### Health & Info

#### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "hellosales-backend"
}
```

**Implementation**: `app/main.py:287-289`

#### GET /health/ready
Readiness check for deployments.

**Response**:
```json
{
  "status": "ready"
}
```

**Implementation**: `app/main.py:292-316`

### Authentication

#### GET /api/v1/auth/me
Get current user profile.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "displayName": "John Doe",
  "authProvider": "workos"
}
```

**Implementation**: `app/api/http/auth.py`

### Profile

#### GET /api/v1/profile
Get user profile with skills and progress.

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "displayName": "John Doe",
  "skills": [...],
  "progress": {...}
}
```

#### PATCH /api/v1/profile
Update user profile.

**Body**:
```json
{
  "displayName": "Updated Name"
}
```

**Implementation**: `app/api/http/profile.py`

### Organizations

#### GET /api/v1/orgs
List organizations user belongs to.

**Response**:
```json
[
  {
    "id": "uuid",
    "orgId": "org_123",
    "name": "Acme Corp",
    "role": "admin"
  }
]
```

**Implementation**: `app/api/http/orgs.py`

### Sailwind (Sales Playbook)

#### Clients

##### GET /api/v1/sailwind/clients
List all clients.

**Query Parameters**:
- `include_archived` (boolean, default: false) - Include archived clients

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "Acme Inc",
    "industry": "Technology",
    "clientArchetypeId": "uuid | null",
    "organizationId": "uuid",
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z",
    "archived": false
  }
]
```

**Implementation**: `app/api/http/sailwind.py:80-130`

##### POST /api/v1/sailwind/clients
Create new client.

**Body**:
```json
{
  "name": "Acme Inc",
  "industry": "Technology",
  "clientArchetypeId": "uuid"
}
```

**Response**: `ClientResponse` (same as GET)

**Implementation**: `app/api/http/sailwind.py:132-142`

##### GET /api/v1/sailwind/clients/{clientId}
Get single client by ID.

**Response**: `ClientResponse`

**Implementation**: `app/api/http/sailwind.py:100-104`

##### PATCH /api/v1/sailwind/clients/{clientId}
Update client.

**Body**:
```json
{
  "name": "Updated Name",
  "industry": "Finance",
  "clientArchetypeId": null,
  "archived": true
}
```

**Response**: `ClientResponse`

**Implementation**: `app/api/http/sailwind.py:144-156`

##### DELETE /api/v1/sailwind/clients/{clientId}
Archive client (soft delete).

**Implementation**: `app/api/http/sailwind.py:158-166`

#### Products

##### GET /api/v1/sailwind/products
List all products.

**Query Parameters**:
- `include_archived` (boolean, default: false)

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "Enterprise Plan",
    "productArchetypeId": "uuid | null",
    "organizationId": "uuid",
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z",
    "archived": false
  }
]
```

**Implementation**: `app/api/http/sailwind.py:168-180`

##### POST /api/v1/sailwind/products
Create new product.

**Body**:
```json
{
  "name": "New Product",
  "productArchetypeId": "uuid"
}
```

**Response**: `ProductResponse`

**Implementation**: `app/api/http/sailwind.py:182-192`

##### GET /api/v1/sailwind/products/{productId}
Get single product.

**Response**: `ProductResponse`

**Implementation**: `app/api/http/sailwind.py:194-198`

##### PATCH /api/v1/sailwind/products/{productId}
Update product.

**Implementation**: `app/api/http/sailwind.py:200-212`

##### DELETE /api/v1/sailwind/products/{productId}
Archive product.

**Implementation**: `app/api/http/sailwind.py:214-222`

#### Strategies

##### GET /api/v1/sailwind/strategies
List all strategies.

**Query Parameters**:
- `include_archived` (boolean, default: false)

**Response**:
```json
[
  {
    "id": "uuid",
    "productId": "uuid",
    "clientId": "uuid",
    "strategyText": "Focus on pain points...",
    "status": "draft | approved | archived",
    "organizationId": "uuid",
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z",
    "archived": false
  }
]
```

**Implementation**: `app/api/http/sailwind.py:224-236`

##### POST /api/v1/sailwind/strategies
Create strategy.

**Body**:
```json
{
  "productId": "uuid",
  "clientId": "uuid",
  "strategyText": "Strategy description",
  "status": "draft"
}
```

**Response**: `StrategyResponse`

**Implementation**: `app/api/http/sailwind.py:238-250`

##### PATCH /api/v1/sailwind/strategies/{strategyId}
Update strategy.

**Body**:
```json
{
  "strategyText": "Updated strategy",
  "status": "approved",
  "archived": false
}
```

**Response**: `StrategyResponse`

**Implementation**: `app/api/http/sailwind.py:252-264`

#### Rep Assignments

##### GET /api/v1/sailwind/my/rep-assignments
Get current user's rep assignments.

**Response**:
```json
[
  {
    "id": "uuid",
    "userId": "uuid",
    "productId": "uuid",
    "clientId": "uuid",
    "strategyId": "uuid | null",
    "minPracticeMinutes": 30,
    "organizationId": "uuid",
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z"
  }
]
```

**Implementation**: `app/api/http/sailwind.py:266-272`

##### POST /api/v1/sailwind/rep-assignments
Create rep assignment (admin only).

**Body**:
```json
{
  "userId": "uuid",
  "productId": "uuid",
  "clientId": "uuid",
  "strategyId": "uuid",
  "minPracticeMinutes": 30
}
```

**Implementation**: `app/api/http/sailwind.py:274-282`

#### Practice Sessions

##### GET /api/v1/sailwind/my/practice-sessions
Get current user's practice sessions.

**Query Parameters**:
- `limit` (integer, default: 50)

**Response**:
```json
[
  {
    "id": "uuid",
    "userId": "uuid",
    "strategyId": "uuid | null",
    "repAssignmentId": "uuid | null",
    "organizationId": "uuid",
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z"
  }
]
```

**Implementation**: `app/api/http/sailwind.py:284-292`

##### POST /api/v1/sailwind/practice-sessions
Start a new practice session.

**Body**:
```json
{
  "strategyId": "uuid",
  "repAssignmentId": "uuid"
}
```

**Response**: `PracticeSessionResponse`

**Implementation**: `app/api/http/sailwind.py:294-306`

#### Client Archetypes

##### GET /api/v1/sailwind/client-archetypes
List client archetypes (templates).

**Implementation**: `app/api/http/sailwind.py:308-314`

##### POST /api/v1/sailwind/client-archetypes
Create client archetype (admin only).

#### Product Archetypes

##### GET /api/v1/sailwind/product-archetypes
List product archetypes.

**Implementation**: `app/api/http/sailwind.py:316-322`

## WebSocket API

### Connection

**Endpoint**: `ws://localhost:8000/ws`

**Implementation**: `app/api/ws/endpoint.py:817`

### Message Format

All messages follow this structure:

```typescript
{
  type: string;      // Message type identifier
  payload?: any;     // Message payload (type-specific)
}
```

### Message Types

#### Authentication

##### Type: `auth`

Authenticate the WebSocket connection.

**Payload**:
```json
{
  "token": "workos_jwt_or_dev_token",
  "platform": "web" | "native"
}
```

**Response**:
```json
{
  "type": "auth.success",
  "payload": {
    "userId": "uuid",
    "sessionId": "uuid | null",
    "orgId": "uuid"
  }
}
```

**Error Response**:
```json
{
  "type": "auth.error",
  "payload": {
    "code": "INVALID_TOKEN",
    "message": "Token verification failed"
  }
}
```

**Implementation**: `app/api/ws/handlers/auth.py`

#### Ping

##### Type: `ping`

Keep-alive ping.

**Response**:
```json
{
  "type": "pong",
  "payload": {
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

**Implementation**: `app/api/ws/handlers/ping.py`

#### Chat

##### Type: `chat`

Send chat message.

**Payload**:
```json
{
  "content": "Hello, how can I improve my sales pitch?"
}
```

**Response (streamed)**:
```json
{
  "type": "chat.chunk",
  "payload": {
    "content": "To improve your sales pitch..."
  }
}
```

```json
{
  "type": "chat.complete",
  "payload": {
    "messageId": "uuid",
    "fullContent": "Complete message text..."
  }
}
```

**Implementation**: `app/api/ws/handlers/chat.py`

#### Voice

##### Type: `voice`

Send audio for speech-to-text processing.

**Payload**:
```json
{
  "audioData": "base64_encoded_audio",
  "format": "wav | mp3",
  "sampleRate": 16000
}
```

**Response**:
```json
{
  "type": "voice.transcript",
  "payload": {
    "transcript": "Transcribed text",
    "confidence": 0.95
  }
}
```

**Implementation**: `app/api/ws/handlers/voice.py`

#### Session

##### Type: `session.start`

Start a new session.

**Payload**:
```json
{
  "service": "chat" | "voice"
}
```

**Response**:
```json
{
  "type": "session.started",
  "payload": {
    "sessionId": "uuid"
  }
}
```

**Implementation**: `app/api/ws/handlers/session.py`

##### Type: `session.end`

End current session.

**Response**:
```json
{
  "type": "session.ended",
  "payload": {
    "sessionId": "uuid",
    "duration": 12345
  }
}
```

#### Pipeline

##### Type: `pipeline.cancel`

Cancel running pipeline.

**Implementation**: `app/api/ws/handlers/pipeline.py`

#### Feedback

##### Type: `feedback`

Submit feedback on AI response.

**Payload**:
```json
{
  "messageId": "uuid",
  "rating": 1-5,
  "comment": "Helpful response"
}
```

**Implementation**: `app/api/ws/handlers/feedback.py`

#### Profile

##### Type: `profile.update`

Update user profile via WebSocket.

**Implementation**: `app/api/ws/handlers/profile.py`

### Error Responses

All errors follow this format:

```json
{
  "type": "error",
  "payload": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
}
```

**Error Codes**:
- `INVALID_MESSAGE` - Missing type field
- `UNKNOWN_MESSAGE_TYPE` - Unhandled message type
- `UNAUTHORIZED` - Not authenticated
- `FORBIDDEN` - Permission denied
- `VALIDATION_ERROR` - Invalid payload

**Implementation**: `app/api/ws/router.py:66-101`

## CORS

Development mode allows all origins. Production requires explicit CORS configuration.

**Implementation**: `app/main.py:95-123`

## Error Responses

HTTP errors follow this format:

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

**Status Codes**:
- `400` - Bad Request / Validation Error
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## OpenAPI Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Implementation**: Auto-generated from FastAPI routes
