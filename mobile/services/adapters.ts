/**
 * Type adapters to convert between API schema types and UI model types
 */

import type {
  ClientResponse,
  ProductResponse,
  RepAssignmentResponse,
  ClientArchetypeResponse,
  ProductArchetypeResponse,
} from './api';

// UI model types (matching existing mockData.ts)
export interface Client {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  location: string;
  status: 'active' | 'inactive' | 'prospect';
  totalRevenue: number;
  lastContact: string;
  avatar?: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  price: number;
  stock: number;
  status: 'available' | 'out_of_stock' | 'discontinued';
  description: string;
  image?: string;
}

export interface SalesRep {
  id: string;
  name: string;
  email: string;
  phone: string;
  territory: string;
  status: 'active' | 'inactive';
  totalSales: number;
  target: number;
  clients: number;
  performance: number;
  avatar?: string;
}

// Adapter functions
export function adaptClientResponse(apiClient: ClientResponse): Client {
  // The backend uses 'name' for the client name and has an 'industry' field
  // We map industry to company for the UI
  return {
    id: apiClient.id,
    name: apiClient.name,
    company: apiClient.industry || 'Unknown Company',
    email: `${apiClient.id}@example.com`, // Placeholder - backend doesn't have email
    phone: '', // Placeholder - backend doesn't have phone
    location: '', // Placeholder - backend doesn't have location
    status: apiClient.archived ? 'inactive' : 'active',
    totalRevenue: 0, // Backend doesn't track revenue
    lastContact: apiClient.created_at.split('T')[0],
  };
}

export function adaptProductResponse(apiProduct: ProductResponse): Product {
  // The backend uses 'name' for product name
  // We need to generate SKU, price, stock from placeholders
  return {
    id: apiProduct.id,
    name: apiProduct.name,
    sku: `SKU-${apiProduct.id.substring(0, 8).toUpperCase()}`,
    category: 'General', // Backend doesn't have category yet
    price: 0, // Backend doesn't have price
    stock: 0, // Backend doesn't have stock
    status: apiProduct.archived ? 'discontinued' : 'available',
    description: '', // Backend doesn't have description
  };
}

export function adaptSalesRepResponse(
  assignment: RepAssignmentResponse,
  archetype?: ClientArchetypeResponse | ProductArchetypeResponse
): SalesRep {
  // Rep assignments link users to products/clients
  // We create a representative SalesRep from the assignment data
  return {
    id: assignment.user_id,
    name: `Rep ${assignment.user_id.substring(0, 8)}`, // Placeholder
    email: `rep@example.com`, // Placeholder
    phone: '', // Placeholder
    territory: 'Assigned Territory',
    status: 'active',
    totalSales: 0,
    target: assignment.min_practice_minutes * 100, // Derived target
    clients: 1, // At least the assigned client
    performance: 100, // Default
  };
}

// Batch adapters
export function adaptClientsResponse(apiClients: ClientResponse[]): Client[] {
  return apiClients.map(adaptClientResponse);
}

export function adaptProductsResponse(apiProducts: ProductResponse[]): Product[] {
  return apiProducts.map(adaptProductResponse);
}

export function adaptSalesRepsResponse(
  assignments: RepAssignmentResponse[],
  _archetypes?: (ClientArchetypeResponse | ProductArchetypeResponse)[]
): SalesRep[] {
  // Group assignments by user to create unique sales reps
  const userToAssignments = new Map<string, RepAssignmentResponse[]>();

  for (const assignment of assignments) {
    const existing = userToAssignments.get(assignment.user_id) || [];
    existing.push(assignment);
    userToAssignments.set(assignment.user_id, existing);
  }

  const salesReps: SalesRep[] = [];

  for (const [userId, userAssignments] of userToAssignments) {
    const totalClients = userAssignments.length;
    const totalMinutes = userAssignments.reduce((sum, a) => sum + a.min_practice_minutes, 0);

    salesReps.push({
      id: userId,
      name: `Sales Rep`, // Would need user lookup from backend
      email: `rep-${userId.substring(0, 8)}@company.com`,
      phone: '',
      territory: 'Territory',
      status: 'active',
      totalSales: 0,
      target: totalMinutes * 100,
      clients: totalClients,
      performance: 100,
    });
  }

  return salesReps;
}
