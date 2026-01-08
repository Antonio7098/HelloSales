import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DollarSign, Users, Package, ShoppingCart } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back to HelloSales.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$48,352</div>
            <p className="text-xs text-muted-foreground">+12.5% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Clients</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,847</div>
            <p className="text-xs text-muted-foreground">+8.2% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,234</div>
            <p className="text-xs text-muted-foreground">+23 new this month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">156</div>
            <p className="text-xs text-muted-foreground">-5.2% from last month</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Recent changes to your sales data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-8">
              <div className="flex items-center">
                <div className="h-2 w-2 rounded-full bg-emerald-500 mr-4" />
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">New order #1234</p>
                  <p className="text-xs text-muted-foreground">Client: Acme Corp</p>
                </div>
                <div className="ml-auto text-xs text-muted-foreground">2 hours ago</div>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 rounded-full bg-blue-500 mr-4" />
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">Product updated</p>
                  <p className="text-xs text-muted-foreground">Premium Plan</p>
                </div>
                <div className="ml-auto text-xs text-muted-foreground">4 hours ago</div>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 rounded-full bg-amber-500 mr-4" />
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">New client registered</p>
                  <p className="text-xs text-muted-foreground">John Doe</p>
                </div>
                <div className="ml-auto text-xs text-muted-foreground">6 hours ago</div>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 rounded-full bg-emerald-500 mr-4" />
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">Order completed</p>
                  <p className="text-xs text-muted-foreground">Order #1230</p>
                </div>
                <div className="ml-auto text-xs text-muted-foreground">8 hours ago</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and actions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-sm text-muted-foreground">
              Use the sidebar navigation to manage your products, clients, users, and more.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
