/**
 * API Client for connecting hellosales-mobile to hellosales-backend
 */

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiClientOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: Record<string, unknown>;
  requiresAuth?: boolean;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // TODO: Implement secure token retrieval from expo-secure-store
    // const token = await SecureStore.getItemAsync('auth_token');
    // if (token) {
    //   headers['Authorization'] = `Bearer ${token}`;
    // }

    return headers;
  }

  async request<T>(endpoint: string, options: ApiClientOptions = {}): Promise<T> {
    const { method = 'GET', body, requiresAuth = true } = options;

    const headers = requiresAuth ? await this.getAuthHeaders() : { 'Content-Type': 'application/json' };

    const config: RequestInit = {
      method,
      headers,
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle empty responses
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  }

  // Convenience methods
  async get<T>(endpoint: string, requiresAuth = true): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', requiresAuth });
  }

  async post<T>(endpoint: string, body: Record<string, unknown>, requiresAuth = true): Promise<T> {
    return this.request<T>(endpoint, { method: 'POST', body, requiresAuth });
  }

  async patch<T>(endpoint: string, body: Record<string, unknown>, requiresAuth = true): Promise<T> {
    return this.request<T>(endpoint, { method: 'PATCH', body, requiresAuth });
  }

  async delete(endpoint: string, requiresAuth = true): Promise<void> {
    await this.request(endpoint, { method: 'DELETE', requiresAuth });
  }
}

export const api = new ApiClient();

// Salon API endpoints
export const sailwindApi = {
  // Clients
  listClients: (includeArchived = false) =>
    api.get<ClientResponse[]>(`/api/v1/sailwind/clients?include_archived=${includeArchived}`),

  getClient: (clientId: string) =>
    api.get<ClientResponse>(`/api/v1/sailwind/clients/${clientId}`),

  createClient: (data: ClientCreateRequest) =>
    api.post<ClientResponse>('/api/v1/sailwind/clients', data),

  updateClient: (clientId: string, data: ClientUpdateRequest) =>
    api.patch<ClientResponse>(`/api/v1/sailwind/clients/${clientId}`, data),

  // Products
  listProducts: (includeArchived = false) =>
    api.get<ProductResponse[]>(`/api/v1/sailwind/products?include_archived=${includeArchived}`),

  getProduct: (productId: string) =>
    api.get<ProductResponse>(`/api/v1/sailwind/products/${productId}`),

  createProduct: (data: ProductCreateRequest) =>
    api.post<ProductResponse>('/api/v1/sailwind/products', data),

  updateProduct: (productId: string, data: ProductUpdateRequest) =>
    api.patch<ProductResponse>(`/api/v1/sailwind/products/${productId}`, data),

  // Strategies
  listStrategies: (includeArchived = false) =>
    api.get<StrategyResponse[]>(`/api/v1/sailwind/strategies?include_archived=${includeArchived}`),

  createStrategy: (data: StrategyCreateRequest) =>
    api.post<StrategyResponse>('/api/v1/sailwind/strategies', data),

  updateStrategy: (strategyId: string, data: StrategyUpdateRequest) =>
    api.patch<StrategyResponse>(`/api/v1/sailwind/strategies/${strategyId}`, data),

  // Rep Assignments
  listMyRepAssignments: () =>
    api.get<RepAssignmentResponse[]>('/api/v1/sailwind/my/rep-assignments'),

  listRepAssignments: () =>
    api.get<RepAssignmentResponse[]>('/api/v1/sailwind/rep-assignments'),

  createRepAssignment: (data: RepAssignmentCreateRequest) =>
    api.post<RepAssignmentResponse>('/api/v1/sailwind/rep-assignments', data),

  // Practice Sessions
  listMyPracticeSessions: (limit = 50) =>
    api.get<PracticeSessionResponse[]>(`/api/v1/sailwind/my/practice-sessions?limit=${limit}`),

  startPracticeSession: (data: PracticeSessionCreateRequest) =>
    api.post<PracticeSessionResponse>('/api/v1/sailwind/practice-sessions', data),

  // Archetypes
  listClientArchetypes: (includeArchived = false) =>
    api.get<ClientArchetypeResponse[]>(`/api/v1/sailwind/client-archetypes?include_archived=${includeArchived}`),

  listProductArchetypes: (includeArchived = false) =>
    api.get<ProductArchetypeResponse[]>(`/api/v1/sailwind/product-archetypes?include_archived=${includeArchived}`),
};

// Schema types matching backend schemas
export interface ClientResponse {
  id: string;
  name: string;
  industry: string | null;
  client_archetype_id: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

export interface ClientCreateRequest {
  name: string;
  industry?: string;
  client_archetype_id?: string;
}

export interface ClientUpdateRequest {
  name?: string;
  industry?: string | null;
  client_archetype_id?: string | null;
  archived?: boolean;
}

export interface ProductResponse {
  id: string;
  name: string;
  product_archetype_id: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

export interface ProductCreateRequest {
  name: string;
  product_archetype_id?: string;
}

export interface ProductUpdateRequest {
  name?: string;
  product_archetype_id?: string | null;
  archived?: boolean;
}

export interface StrategyResponse {
  id: string;
  product_id: string;
  client_id: string;
  strategy_text: string | null;
  status: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

export interface StrategyCreateRequest {
  product_id: string;
  client_id: string;
  strategy_text?: string;
  status?: string;
}

export interface StrategyUpdateRequest {
  strategy_text?: string | null;
  status?: string | null;
  archived?: boolean;
}

export interface RepAssignmentResponse {
  id: string;
  user_id: string;
  product_id: string;
  client_id: string;
  strategy_id: string | null;
  min_practice_minutes: number;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface RepAssignmentCreateRequest {
  user_id: string;
  product_id: string;
  client_id: string;
  strategy_id?: string;
  min_practice_minutes?: number;
}

export interface PracticeSessionResponse {
  id: string;
  user_id: string;
  strategy_id: string | null;
  rep_assignment_id: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface PracticeSessionCreateRequest {
  strategy_id?: string;
  rep_assignment_id?: string;
}

export interface ClientArchetypeResponse {
  id: string;
  name: string;
  industry: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

export interface ProductArchetypeResponse {
  id: string;
  name: string;
  organization_id: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}
