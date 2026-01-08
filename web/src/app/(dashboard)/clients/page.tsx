'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"

interface Client {
  id: string
  name: string
  email: string
  phone: string
  company: string
  status: 'active' | 'inactive' | 'prospect'
  totalRevenue: number
}

const mockClients: Client[] = [
  { id: '1', name: 'Acme Corporation', email: 'contact@acme.com', phone: '+1 (555) 123-4567', company: 'Acme Corp', status: 'active', totalRevenue: 125000 },
  { id: '2', name: 'TechStart Inc', email: 'info@techstart.io', phone: '+1 (555) 234-5678', company: 'TechStart', status: 'active', totalRevenue: 85000 },
  { id: '3', name: 'Global Solutions', email: 'sales@globalsol.com', phone: '+1 (555) 345-6789', company: 'Global Solutions', status: 'prospect', totalRevenue: 0 },
  { id: '4', name: 'Innovation Labs', email: 'hello@innovlabs.co', phone: '+1 (555) 456-7890', company: 'Innovation Labs', status: 'active', totalRevenue: 210000 },
  { id: '5', name: 'Startup Ventures', email: 'contact@startupv.com', phone: '+1 (555) 567-8901', company: 'Startup Ventures', status: 'inactive', totalRevenue: 35000 },
]

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value)
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>(mockClients)
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingClient, setEditingClient] = useState<Client | null>(null)
  const [formData, setFormData] = useState({ name: '', email: '', phone: '', company: '' })

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(search.toLowerCase()) ||
    client.email.toLowerCase().includes(search.toLowerCase()) ||
    client.company.toLowerCase().includes(search.toLowerCase())
  )

  const handleAdd = () => {
    setEditingClient(null)
    setFormData({ name: '', email: '', phone: '', company: '' })
    setDialogOpen(true)
  }

  const handleEdit = (client: Client) => {
    setEditingClient(client)
    setFormData({ name: client.name, email: client.email, phone: client.phone, company: client.company })
    setDialogOpen(true)
  }

  const handleDelete = (id: string) => {
    setClients(clients.filter(c => c.id !== id))
  }

  const handleSave = () => {
    if (editingClient) {
      setClients(clients.map(c =>
        c.id === editingClient.id
          ? { ...c, ...formData }
          : c
      ))
    } else {
      const newClient: Client = {
        id: String(Date.now()),
        ...formData,
        status: 'prospect',
        totalRevenue: 0,
      }
      setClients([...clients, newClient])
    }
    setDialogOpen(false)
  }

  const getStatusBadge = (status: Client['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="secondary">Active</Badge>
      case 'inactive':
        return <Badge variant="outline">Inactive</Badge>
      case 'prospect':
        return <Badge className="bg-blue-100 text-blue-800">Prospect</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clients</h1>
          <p className="text-muted-foreground">
            Manage your client relationships
          </p>
        </div>
        <Button onClick={handleAdd}>
          <span className="mr-2">+</span>
          Add Client
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Clients</CardTitle>
          <CardDescription>
            {filteredClients.length} clients
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <Input
              placeholder="Search clients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
          </div>
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Name</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Email</th>
                  <th className="h-10 px-4 text-center align-middle font-medium text-muted-foreground">Status</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Revenue</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredClients.map((client) => (
                  <tr key={client.id} className="border-b">
                    <td className="p-4 font-medium">{client.name}</td>
                    <td className="p-4">{client.company}</td>
                    <td className="p-4 text-muted-foreground">{client.email}</td>
                    <td className="p-4 text-center">{getStatusBadge(client.status)}</td>
                    <td className="p-4 text-right">{formatCurrency(client.totalRevenue)}</td>
                    <td className="p-4 text-right">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(client)} className="mr-2">
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(client.id)} className="text-destructive">
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingClient ? 'Edit Client' : 'Add Client'}</DialogTitle>
            <DialogDescription>
              {editingClient ? 'Update client details' : 'Add a new client to your CRM'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="name">Name</label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Full name or company name"
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="email">Email</label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="email@example.com"
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="phone">Phone</label>
              <Input
                id="phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+1 (555) 123-4567"
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="company">Company</label>
              <Input
                id="company"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                placeholder="Company name"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave}>{editingClient ? 'Save Changes' : 'Add Client'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
