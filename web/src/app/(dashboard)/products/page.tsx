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

interface Product {
  id: string
  name: string
  category: string
  price: number
  stock: number
  status: 'active' | 'inactive' | 'out-of-stock'
}

const mockProducts: Product[] = [
  { id: '1', name: 'Premium Plan', category: 'Subscription', price: 99.99, stock: 999, status: 'active' },
  { id: '2', name: 'Enterprise Plan', category: 'Subscription', price: 299.99, stock: 999, status: 'active' },
  { id: '3', name: 'Basic Plan', category: 'Subscription', price: 49.99, stock: 0, status: 'out-of-stock' },
  { id: '4', name: 'Add-on: Analytics', category: 'Add-on', price: 19.99, stock: 999, status: 'active' },
  { id: '5', name: 'Add-on: API Access', category: 'Add-on', price: 49.99, stock: 150, status: 'active' },
]

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>(mockProducts)
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [formData, setFormData] = useState({ name: '', category: '', price: '', stock: '' })

  const filteredProducts = products.filter(product =>
    product.name.toLowerCase().includes(search.toLowerCase()) ||
    product.category.toLowerCase().includes(search.toLowerCase())
  )

  const handleAdd = () => {
    setEditingProduct(null)
    setFormData({ name: '', category: '', price: '', stock: '' })
    setDialogOpen(true)
  }

  const handleEdit = (product: Product) => {
    setEditingProduct(product)
    setFormData({ name: product.name, category: product.category, price: product.price.toString(), stock: product.stock.toString() })
    setDialogOpen(true)
  }

  const handleDelete = (id: string) => {
    setProducts(products.filter(p => p.id !== id))
  }

  const handleSave = () => {
    if (editingProduct) {
      setProducts(products.map(p =>
        p.id === editingProduct.id
          ? { ...p, name: formData.name, category: formData.category, price: parseFloat(formData.price), stock: parseInt(formData.stock), status: parseInt(formData.stock) > 0 ? 'active' : 'out-of-stock' }
          : p
      ))
    } else {
      const newProduct: Product = {
        id: String(Date.now()),
        name: formData.name,
        category: formData.category,
        price: parseFloat(formData.price),
        stock: parseInt(formData.stock),
        status: parseInt(formData.stock) > 0 ? 'active' : 'out-of-stock',
      }
      setProducts([...products, newProduct])
    }
    setDialogOpen(false)
  }

  const getStatusBadge = (status: Product['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="secondary">Active</Badge>
      case 'inactive':
        return <Badge variant="outline">Inactive</Badge>
      case 'out-of-stock':
        return <Badge variant="destructive">Out of Stock</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Products</h1>
          <p className="text-muted-foreground">
            Manage your products and services
          </p>
        </div>
        <Button onClick={handleAdd}>
          <span className="mr-2">+</span>
          Add Product
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Products</CardTitle>
          <CardDescription>
            {filteredProducts.length} items
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <Input
              placeholder="Search products..."
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
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Category</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Price</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Stock</th>
                  <th className="h-10 px-4 text-center align-middle font-medium text-muted-foreground">Status</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => (
                  <tr key={product.id} className="border-b">
                    <td className="p-4">{product.name}</td>
                    <td className="p-4">{product.category}</td>
                    <td className="p-4 text-right">{formatCurrency(product.price)}</td>
                    <td className="p-4 text-right">{product.stock}</td>
                    <td className="p-4 text-center">{getStatusBadge(product.status)}</td>
                    <td className="p-4 text-right">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(product)} className="mr-2">
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(product.id)} className="text-destructive">
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
            <DialogTitle>{editingProduct ? 'Edit Product' : 'Add Product'}</DialogTitle>
            <DialogDescription>
              {editingProduct ? 'Update product details' : 'Add a new product to your catalog'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="name">Name</label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Product name"
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="category">Category</label>
              <Input
                id="category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                placeholder="Category"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <label htmlFor="price">Price</label>
                <Input
                  id="price"
                  type="number"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div className="grid gap-2">
                <label htmlFor="stock">Stock</label>
                <Input
                  id="stock"
                  type="number"
                  value={formData.stock}
                  onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                  placeholder="0"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave}>{editingProduct ? 'Save Changes' : 'Add Product'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
