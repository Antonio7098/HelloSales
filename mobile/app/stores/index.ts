import { create } from 'zustand';
import { sailwindApi, adaptClientsResponse, adaptProductsResponse, adaptSalesRepsResponse } from '../../services';
import { Client, Product, SalesRep, mockClients, mockProducts, mockSalesReps } from '../../data/mockData';

// Feature flag for using real API vs mock data
const USE_API = process.env.EXPO_USE_API === 'true';

interface ClientsStore {
  clients: Client[];
  filteredClients: Client[];
  searchQuery: string;
  statusFilter: 'all' | 'active' | 'inactive' | 'prospect';
  selectedClient: Client | null;
  isLoading: boolean;
  error: string | null;

  setSearchQuery: (query: string) => void;
  setStatusFilter: (status: 'all' | 'active' | 'inactive' | 'prospect') => void;
  selectClient: (client: Client | null) => void;
  filterClients: () => void;
  loadClients: () => Promise<void>;
}

export const useClientsStore = create<ClientsStore>((set, get) => ({
  clients: [],
  filteredClients: [],
  searchQuery: '',
  statusFilter: 'all',
  selectedClient: null,
  isLoading: false,
  error: null,

  setSearchQuery: (query) => {
    set({ searchQuery: query });
    get().filterClients();
  },

  setStatusFilter: (status) => {
    set({ statusFilter: status });
    get().filterClients();
  },

  selectClient: (client) => set({ selectedClient: client }),

  filterClients: () => {
    const { clients, searchQuery, statusFilter } = get();
    let filtered = [...clients];

    if (statusFilter !== 'all') {
      filtered = filtered.filter((c) => c.status === statusFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.company.toLowerCase().includes(query) ||
          c.email.toLowerCase().includes(query)
      );
    }

    set({ filteredClients: filtered });
  },

  loadClients: async () => {
    set({ isLoading: true, error: null });
    try {
      if (USE_API) {
        const apiClients = await sailwindApi.listClients();
        const clients = adaptClientsResponse(apiClients);
        set({ clients, filteredClients: clients });
      } else {
        // Fallback to mock data
        await new Promise((resolve) => setTimeout(resolve, 300));
        set({
          clients: mockClients,
          filteredClients: mockClients,
        });
      }
    } catch (error) {
      console.error('Failed to load clients:', error);
      set({ error: error instanceof Error ? error.message : 'Failed to load clients' });
      // Fallback to mock data on error
      set({
        clients: mockClients,
        filteredClients: mockClients,
      });
    } finally {
      set({ isLoading: false });
    }
  },
}));

interface ProductsStore {
  products: Product[];
  filteredProducts: Product[];
  searchQuery: string;
  categoryFilter: string;
  statusFilter: 'all' | 'available' | 'out_of_stock' | 'discontinued';
  selectedProduct: Product | null;
  isLoading: boolean;
  error: string | null;
  categories: string[];

  setSearchQuery: (query: string) => void;
  setCategoryFilter: (category: string) => void;
  setStatusFilter: (status: 'all' | 'available' | 'out_of_stock' | 'discontinued') => void;
  selectProduct: (product: Product | null) => void;
  filterProducts: () => void;
  loadProducts: () => Promise<void>;
}

export const useProductsStore = create<ProductsStore>((set, get) => ({
  products: [],
  filteredProducts: [],
  searchQuery: '',
  categoryFilter: 'all',
  statusFilter: 'all',
  selectedProduct: null,
  isLoading: false,
  error: null,
  categories: ['all', 'Software', 'Services', 'Hardware'],

  setSearchQuery: (query) => {
    set({ searchQuery: query });
    get().filterProducts();
  },

  setCategoryFilter: (category) => {
    set({ categoryFilter: category });
    get().filterProducts();
  },

  setStatusFilter: (status) => {
    set({ statusFilter: status });
    get().filterProducts();
  },

  selectProduct: (product) => set({ selectedProduct: product }),

  filterProducts: () => {
    const { products, searchQuery, categoryFilter, statusFilter } = get();
    let filtered = [...products];

    if (categoryFilter !== 'all') {
      filtered = filtered.filter((p) => p.category === categoryFilter);
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((p) => p.status === statusFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.sku.toLowerCase().includes(query) ||
          p.description.toLowerCase().includes(query)
      );
    }

    set({ filteredProducts: filtered });
  },

  loadProducts: async () => {
    set({ isLoading: true, error: null });
    try {
      if (USE_API) {
        const apiProducts = await sailwindApi.listProducts();
        const products = adaptProductsResponse(apiProducts);
        set({ products, filteredProducts: products });
      } else {
        await new Promise((resolve) => setTimeout(resolve, 300));
        set({
          products: mockProducts,
          filteredProducts: mockProducts,
        });
      }
    } catch (error) {
      console.error('Failed to load products:', error);
      set({ error: error instanceof Error ? error.message : 'Failed to load products' });
      set({
        products: mockProducts,
        filteredProducts: mockProducts,
      });
    } finally {
      set({ isLoading: false });
    }
  },
}));

interface SalesRepsStore {
  salesReps: SalesRep[];
  filteredSalesReps: SalesRep[];
  searchQuery: string;
  territoryFilter: string;
  statusFilter: 'all' | 'active' | 'inactive';
  selectedSalesRep: SalesRep | null;
  isLoading: boolean;
  error: string | null;
  territories: string[];

  setSearchQuery: (query: string) => void;
  setTerritoryFilter: (territory: string) => void;
  setStatusFilter: (status: 'all' | 'active' | 'inactive') => void;
  selectSalesRep: (salesRep: SalesRep | null) => void;
  filterSalesReps: () => void;
  loadSalesReps: () => Promise<void>;
}

export const useSalesRepsStore = create<SalesRepsStore>((set, get) => ({
  salesReps: [],
  filteredSalesReps: [],
  searchQuery: '',
  territoryFilter: 'all',
  statusFilter: 'all',
  selectedSalesRep: null,
  isLoading: false,
  error: null,
  territories: ['all', 'West Coast', 'Northeast', 'Midwest', 'Southeast', 'Southwest'],

  setSearchQuery: (query) => {
    set({ searchQuery: query });
    get().filterSalesReps();
  },

  setTerritoryFilter: (territory) => {
    set({ territoryFilter: territory });
    get().filterSalesReps();
  },

  setStatusFilter: (status) => {
    set({ statusFilter: status });
    get().filterSalesReps();
  },

  selectSalesRep: (salesRep) => set({ selectedSalesRep: salesRep }),

  filterSalesReps: () => {
    const { salesReps, searchQuery, territoryFilter, statusFilter } = get();
    let filtered = [...salesReps];

    if (territoryFilter !== 'all') {
      filtered = filtered.filter((sr) => sr.territory === territoryFilter);
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((sr) => sr.status === statusFilter);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (sr) =>
          sr.name.toLowerCase().includes(query) ||
          sr.email.toLowerCase().includes(query) ||
          sr.territory.toLowerCase().includes(query)
      );
    }

    set({ filteredSalesReps: filtered });
  },

  loadSalesReps: async () => {
    set({ isLoading: true, error: null });
    try {
      if (USE_API) {
        const assignments = await sailwindApi.listMyRepAssignments();
        const salesReps = adaptSalesRepsResponse(assignments);
        set({ salesReps, filteredSalesReps: salesReps });
      } else {
        await new Promise((resolve) => setTimeout(resolve, 300));
        set({
          salesReps: mockSalesReps,
          filteredSalesReps: mockSalesReps,
        });
      }
    } catch (error) {
      console.error('Failed to load sales reps:', error);
      set({ error: error instanceof Error ? error.message : 'Failed to load sales reps' });
      set({
        salesReps: mockSalesReps,
        filteredSalesReps: mockSalesReps,
      });
    } finally {
      set({ isLoading: false });
    }
  },
}));

interface AppStore {
  currentUserRole: 'admin' | 'rep';
  setCurrentUserRole: (role: 'admin' | 'rep') => void;
}

export const useAppStore = create<AppStore>((set) => ({
  currentUserRole: 'admin',
  setCurrentUserRole: (role) => set({ currentUserRole: role }),
}));

export default useAppStore;
