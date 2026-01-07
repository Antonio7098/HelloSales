# HelloSales Mobile

React Native mobile app with Expo Router and a custom design system.

## Overview

The mobile app provides:
- Client management interface
- Product catalog browsing
- Sales team dashboard
- Real-time API integration

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npx expo start --port 8002

# Scan QR code with Expo Go app
# Or visit http://localhost:8002 for web
```

## Project Structure

```
mobile/
├── app/
│   ├── _components/         # UI Components
│   │   └── ui/           # Design system
│   │       ├── Box.tsx             # Layout primitive
│   │       ├── Button.tsx           # Interactive button
│   │       ├── Card.tsx             # Container component
│   │       ├── Text.tsx             # Typography
│   │       ├── Screen.tsx           # Screen wrapper
│   │       ├── Input.tsx            # Form input
│   │       ├── List.tsx             # List components
│   │       ├── Modal.tsx            # Modal overlay
│   │       ├── Section.tsx          # Content grouping
│   │       ├── Badge.tsx            # Status badge
│   │       ├── StatsCards.tsx        # Stats display
│   │       ├── TabBar.tsx           # Bottom navigation
│   │       ├── context.tsx          # Theme context
│   │       └── index.ts             # Component exports
│   │
│   ├── screens/            # Screen components
│   │   ├── index.tsx          # Home screen
│   │   ├── ClientsScreen.tsx  # Client list
│   │   ├── ProductsScreen.tsx  # Product catalog
│   │   ├── SalesRepsScreen.tsx # Sales reps
│   │   ├── products.tsx       # Products route
│   │   └── team.tsx          # Team route
│   │
│   ├── stores/             # State management
│   │   └── index.ts          # Zustand store
│   │
│   ├── services/           # API clients
│   │   ├── api.ts             # HTTP client
│   │   ├── adapters.ts        # WebSocket (TODO)
│   │   └── index.ts
│   │
│   ├── data/              # Mock data
│   │   └── mockData.ts       # Sample clients/products
│   │
│   ├── theme/             # Design tokens
│   │   └── index.ts          # Colors, spacing, typography
│   │
│   ├── assets/            # Static assets
│   │   ├── adaptive-icon.png
│   │   ├── favicon.png
│   │   ├── icon.png
│   │   └── splash-icon.png
│   │
│   ├── _layout.tsx        # Root layout with theme
│   ├── index.tsx          # Home page
│   ├── App.tsx            # App root
│   └── app.config.ts       # Expo config
│
├── services/               # Shared services
│   └── api.ts             # API client (TODO: consolidate)
│
├── docs/                  # Documentation
│   └── BACKEND_CONNECTION.md
│
├── package.json
├── tsconfig.json
├── babel.config.js
└── metro.config.js
```

## Design System

### Component Hierarchy

```
Layout (ThemeProvider)
 └── Stack (Expo Router)
      └── Screen
            └── VStack / HStack / Box
                  └── UI Components (Text, Card, Button, etc.)
```

### Core Components

#### Layout Primitives

- **Box** (`Box.tsx`) - Generic container with spacing props
- **VStack** - Vertical stack of children
- **HStack** - Horizontal stack of children
- **Flex** - Flexbox layout

#### Typography

- **Text** (`Text.tsx`) - Text with variants:
  - `h1`, `h2`, `h3`, `h4` - Headings
  - `body`, `caption`, `muted` - Body text
- **Heading** (`Text.tsx:22`) - Semantic heading

#### Interactive Elements

- **Button** (`Button.tsx`) - Button with variants:
  - `primary`, `secondary`, `ghost`, `danger`
  - Sizes: `xs`, `sm`, `md`, `lg`
- **IconButton** - Icon-only button

#### Containers

- **Card** (`Card.tsx`) - Bordered container with padding
- **CardPressable** - Pressable card
- **Modal** (`Modal.tsx`) - Full-screen overlay
- **Section** (`Section.tsx`) - Content with title

#### Form Elements

- **Input** (`Input.tsx`) - Text input with validation
- **Form** (`Form.tsx`) - Form wrapper (TODO)

#### Lists

- **List** (`List.tsx`) - Vertical list container
- **ListItem** (`List.tsx:18`) - List item with chevron

#### Screen

- **Screen** (`Screen.tsx`) - Screen wrapper with header
- **ScrollScreen** - Scrollable screen content
- **ScreenHeader** - Header with back button

#### Utility Components

- **Badge** (`Badge.tsx`) - Status badge with colors
- **StatsCards** (`StatsCards.tsx`) - Grid of stat cards
- **StatsCard** - Single stat card
- **SearchInput** - Input with search icon
- **Pagination** - Pagination controls
- **ErrorBoundary** - Error catching

### Theme

**Colors** (`theme/index.ts:10-25`):
```typescript
colors: {
  background: '#0F172A',    // Main background
  card: '#1E293B',          // Card background
  primary: '#F8FAFC',        // Primary text
  secondary: '#94A3B8',      // Secondary text
  muted: '#64748B',          // Muted text
  border: '#334155',         // Border color
  success: '#10B981',        // Success (green)
  warning: '#F59E0B',        // Warning (orange)
  error: '#EF4444',          // Error (red)
}
```

**Spacing**:
```typescript
spacing: {
  xs: 4,    // 4px
  sm: 8,    // 8px
  md: 16,   // 16px
  lg: 24,   // 24px
  xl: 32,   // 32px
}
```

**Typography**:
```typescript
typography: {
  fontSize: {
    h1: 32,
    h2: 28,
    h3: 24,
    h4: 20,
    body: 16,
    caption: 14,
  },
  fontWeight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
}
```

## State Management

### Zustand Store

Located at `app/stores/index.ts`:

```typescript
interface HelloSalesStore {
  // State
  clients: Client[];
  products: Product[];
  salesReps: SalesRep[];
  loading: boolean;
  error: string | null;

  // Actions
  setClients: (clients: Client[]) => void;
  addClient: (client: Client) => void;
  updateClient: (id: string, updates: Partial<Client>) => void;
  deleteClient: (id: string) => void;
  // ... other actions
}

export const useClientsStore = create<HelloSalesStore>((set) => ({
  // Implementations
}));
```

### Using Store

```typescript
import { useClientsStore } from './stores';

function MyScreen() {
  const { clients, loading, setClients } = useClientsStore();

  // Access state
  console.log(clients);

  // Call actions
  const loadClients = async () => {
    const data = await api.listClients();
    setClients(data);
  };
}
```

## API Client

### HTTP Client

Located at `services/api.ts:14-77`:

```typescript
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async request<T>(endpoint: string, options: ApiClientOptions = {}): Promise<T> {
    // Makes HTTP request with auth headers
  }

  // Convenience methods
  async get<T>(endpoint: string, requiresAuth = true): Promise<T>
  async post<T>(endpoint: string, body: Record<string, unknown>, requiresAuth = true): Promise<T>
  async patch<T>(endpoint: string, body: Record<string, unknown>, requiresAuth = true): Promise<T>
  async delete(endpoint: string, requiresAuth = true): Promise<void>
}
```

### API Endpoints

**Sailwind API** (`services/api.ts:81-142`):
- `listClients(includeArchived)` - List all clients
- `getClient(clientId)` - Get single client
- `createClient(data)` - Create new client
- `updateClient(clientId, data)` - Update client
- `listProducts(includeArchived)` - List products
- `createProduct(data)` - Create product
- `listStrategies(includeArchived)` - List strategies
- `listMyRepAssignments()` - Get my assignments
- `listMyPracticeSessions(limit)` - Get my practice sessions
- `startPracticeSession(data)` - Start practice session

### Configuration

**API Base URL** (`services/api.ts:5`):
```typescript
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
```

**Expo Config** (`app.config.ts:29-31`):
```typescript
extra: {
  apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000'
}
```

## Screens

### Clients Screen

**File**: `app/screens/ClientsScreen.tsx`

Features:
- List all clients with search/filter
- View client details
- Create/edit clients
- Status badges (active, inactive, prospect)

**Key Components**:
- `ClientListItem` - List item with chevron
- `ClientDetail` - Client detail modal
- `StatsCards` - Dashboard stats

### Products Screen

**File**: `app/screens/ProductsScreen.tsx`

Features:
- Product catalog
- Search and filter
- Product details
- Inventory tracking

### Sales Reps Screen

**File**: `app/screens/SalesRepsScreen.tsx`

Features:
- Sales team overview
- Performance metrics
- Assignment tracking

## Navigation

### Expo Router

**File**: `app/_layout.tsx`

Layout with theme provider:
```typescript
<ThemeProvider>
  <Stack screenOptions={{ headerShown: false }} />
</ThemeProvider>
```

### Routes

- `/` - Home
- `/products` - Products
- `/team` - Sales reps

**Screens**: `app/index.tsx`, `app/products.tsx`, `app/team.tsx`

## Development

### Commands

```bash
# Start development server
npm start                    # or: npx expo start --port 8002

# Run on iOS
npm run ios

# Run on Android
npm run android

# Build for web
npm run build:web

# TypeScript check
npx tsc --noEmit
```

### Configuration

**app.config.ts**:
- App name: HelloSales
- Bundle ID: com.hellosales.mobile
- API URL: from env var

**Environment**:
```bash
EXPO_PUBLIC_API_URL=http://localhost:8000 npm start
```

## Data Types

### Client

```typescript
interface Client {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  location: string;
  status: 'active' | 'inactive' | 'prospect';
  lastContact: string;
  revenue: number;
}
```

### Product

```typescript
interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  sku: string;
  stock: number;
  status: 'active' | 'discontinued';
}
```

### Strategy

```typescript
interface Strategy {
  id: string;
  productId: string;
  clientId: string;
  strategyText: string | null;
  status: string | null;
  createdAt: string;
  updatedAt: string;
}
```

**Mock Data**: `app/data/mockData.ts`

## Styling

### StyleSheet Pattern

```typescript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: theme.spacing.lg,
  },
});
```

### Theme Access

```typescript
import { theme } from '../theme';

<Text color="primary" style={{ backgroundColor: theme.colors.card }} />
```

## Deployment

### EAS Build

```bash
# Install EAS CLI
npm install -g eas-cli

# Build for iOS
eas build --platform ios

# Build for Android
eas build --platform android

# Build for web
npm run build:web
```

### Environment Variables

Configure in EAS dashboard:
- `EXPO_PUBLIC_API_URL` - Backend API URL

## Testing

```bash
# Run tests (if configured)
npm test

# TypeScript check
npx tsc --noEmit
```

## Notes

- **Auth**: Currently placeholder - token retrieval from `expo-secure-store` TODO (`services/api.ts:25-29`)
- **WebSocket**: WebSocket adapter TODO (`services/adapters.ts`)
- **Offline**: No offline support currently
