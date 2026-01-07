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

export const mockClients: Client[] = [
  {
    id: 'c1',
    name: 'Sarah Johnson',
    company: 'TechCorp Industries',
    email: 'sarah.johnson@techcorp.com',
    phone: '+1 (555) 123-4567',
    location: 'San Francisco, CA',
    status: 'active',
    totalRevenue: 125000,
    lastContact: '2024-01-15',
  },
  {
    id: 'c2',
    name: 'Michael Chen',
    company: 'Global Retail Solutions',
    email: 'mchen@globalretail.com',
    phone: '+1 (555) 234-5678',
    location: 'New York, NY',
    status: 'active',
    totalRevenue: 89000,
    lastContact: '2024-01-10',
  },
  {
    id: 'c3',
    name: 'Emily Rodriguez',
    company: 'HealthFirst Medical',
    email: 'emily.r@healthfirst.org',
    phone: '+1 (555) 345-6789',
    location: 'Miami, FL',
    status: 'active',
    totalRevenue: 210000,
    lastContact: '2024-01-12',
  },
  {
    id: 'c4',
    name: 'David Kim',
    company: 'Pacific Trading Co.',
    email: 'dkim@pacifictrading.com',
    phone: '+1 (555) 456-7890',
    location: 'Seattle, WA',
    status: 'prospect',
    totalRevenue: 0,
    lastContact: '2024-01-14',
  },
  {
    id: 'c5',
    name: 'Amanda Thompson',
    company: 'Thompson Logistics',
    email: 'athompson@thompsonlogistics.com',
    phone: '+1 (555) 567-8901',
    location: 'Chicago, IL',
    status: 'inactive',
    totalRevenue: 45000,
    lastContact: '2023-12-20',
  },
  {
    id: 'c6',
    name: 'Robert Martinez',
    company: 'Martinez & Associates',
    email: 'robert@martinezassoc.com',
    phone: '+1 (555) 678-9012',
    location: 'Los Angeles, CA',
    status: 'active',
    totalRevenue: 178000,
    lastContact: '2024-01-08',
  },
  {
    id: 'c7',
    name: 'Jennifer Lee',
    company: 'Innovate Digital',
    email: 'jlee@innovatedigital.io',
    phone: '+1 (555) 789-0123',
    location: 'Austin, TX',
    status: 'prospect',
    totalRevenue: 0,
    lastContact: '2024-01-11',
  },
  {
    id: 'c8',
    name: 'William Brown',
    company: 'Brown Manufacturing',
    email: 'wbrown@brownmfg.com',
    phone: '+1 (555) 890-1234',
    location: 'Detroit, MI',
    status: 'active',
    totalRevenue: 95000,
    lastContact: '2024-01-13',
  },
];

export const mockProducts: Product[] = [
  {
    id: 'p1',
    name: 'Enterprise License',
    sku: 'ENT-LIC-001',
    category: 'Software',
    price: 5000,
    stock: 100,
    status: 'available',
    description: 'Annual enterprise software license with full feature access',
  },
  {
    id: 'p2',
    name: 'Professional License',
    sku: 'PRO-LIC-001',
    category: 'Software',
    price: 1500,
    stock: 250,
    status: 'available',
    description: 'Annual professional license for small teams',
  },
  {
    id: 'p3',
    name: 'Support Package - Gold',
    sku: 'SUP-GLD-001',
    category: 'Services',
    price: 2500,
    stock: 50,
    status: 'available',
    description: 'Premium 24/7 support with dedicated account manager',
  },
  {
    id: 'p4',
    name: 'Training Session - Onsite',
    sku: 'TRN-ONS-001',
    category: 'Services',
    price: 3000,
    stock: 20,
    status: 'available',
    description: 'Full-day onsite training for up to 10 participants',
  },
  {
    id: 'p5',
    name: 'API Access - Enterprise',
    sku: 'API-ENT-001',
    category: 'Software',
    price: 8000,
    stock: 75,
    status: 'available',
    description: 'Unlimited API access with SLA guarantee',
  },
  {
    id: 'p6',
    name: 'Starter Kit',
    sku: 'KIT-STR-001',
    category: 'Hardware',
    price: 750,
    stock: 0,
    status: 'out_of_stock',
    description: 'Hardware starter kit for new implementations',
  },
  {
    id: 'p7',
    name: 'Add-on: Analytics Module',
    sku: 'ADD-ANA-001',
    category: 'Software',
    price: 1200,
    stock: 200,
    status: 'available',
    description: 'Advanced analytics and reporting module',
  },
  {
    id: 'p8',
    name: 'Add-on: Security Suite',
    sku: 'ADD-SEC-001',
    category: 'Software',
    price: 2000,
    stock: 150,
    status: 'available',
    description: 'Enhanced security and compliance features',
  },
];

export const mockSalesReps: SalesRep[] = [
  {
    id: 'sr1',
    name: 'Alex Thompson',
    email: 'alex.thompson@salewind.com',
    phone: '+1 (555) 111-2222',
    territory: 'West Coast',
    status: 'active',
    totalSales: 485000,
    target: 500000,
    clients: 24,
    performance: 97,
  },
  {
    id: 'sr2',
    name: 'Jessica Wang',
    email: 'jessica.wang@salewind.com',
    phone: '+1 (555) 222-3333',
    territory: 'Northeast',
    status: 'active',
    totalSales: 520000,
    target: 480000,
    clients: 31,
    performance: 108,
  },
  {
    id: 'sr3',
    name: 'Marcus Johnson',
    email: 'marcus.johnson@salewind.com',
    phone: '+1 (555) 333-4444',
    territory: 'Midwest',
    status: 'active',
    totalSales: 380000,
    target: 400000,
    clients: 18,
    performance: 95,
  },
  {
    id: 'sr4',
    name: 'Rachel Garcia',
    email: 'rachel.garcia@salewind.com',
    phone: '+1 (555) 444-5555',
    territory: 'Southeast',
    status: 'active',
    totalSales: 445000,
    target: 420000,
    clients: 27,
    performance: 106,
  },
  {
    id: 'sr5',
    name: 'David Park',
    email: 'david.park@salewind.com',
    phone: '+1 (555) 555-6666',
    territory: 'Southwest',
    status: 'inactive',
    totalSales: 210000,
    target: 400000,
    clients: 12,
    performance: 52,
  },
  {
    id: 'sr6',
    name: 'Emily Davis',
    email: 'emily.davis@salewind.com',
    phone: '+1 (555) 666-7777',
    territory: 'Northeast',
    status: 'active',
    totalSales: 390000,
    target: 380000,
    clients: 22,
    performance: 103,
  },
];

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatPercent(value: number): string {
  return `${value.toFixed(0)}%`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
