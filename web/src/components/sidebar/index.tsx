'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  LayoutDashboard,
  Package,
  Users,
  UserCog,
  Settings,
  HelpCircle,
} from 'lucide-react'
import { useSidebar } from '@/hooks/use-sidebar'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Products', href: '/products', icon: Package },
  { name: 'Clients', href: '/clients', icon: Users },
  { name: 'Users', href: '/users', icon: UserCog },
]

const secondaryNavigation = [
  { name: 'Settings', href: '/settings', icon: Settings },
  { name: 'Help', href: '/help', icon: HelpCircle },
]

export function Sidebar() {
  const pathname = usePathname()
  const { hovered, setHovered } = useSidebar()
  const isExpanded = hovered

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-card overflow-hidden',
        isExpanded ? 'w-[260px]' : 'w-[60px]'
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className={cn(
          'flex h-16 items-center border-b px-3 transition-all duration-200',
          isExpanded ? 'justify-start gap-3' : 'justify-center'
        )}>
          {/* HS Icon - Always anchored */}
          <div className="h-8 w-8 rounded-lg border-2 border-primary flex items-center justify-center shrink-0">
            <span className="text-primary font-bold text-sm">HS</span>
          </div>
          {/* HelloSales - Slides in from right */}
          <div
            className={cn(
              'overflow-hidden transition-all duration-300',
              isExpanded ? 'w-auto opacity-100 ml-3' : 'w-0 opacity-0 ml-0'
            )}
          >
            <span className="text-lg font-semibold whitespace-nowrap">
              HelloSales
            </span>
          </div>
        </div>

        {/* Main Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-1 px-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              const Icon = item.icon

              const linkElement = (
                <Link
                  href={item.href}
                  className={cn(
                    'flex h-9 items-center rounded-md px-3 text-sm transition-colors',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isExpanded ? 'justify-start gap-3' : 'justify-center'
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {/* Text - Hidden when collapsed */}
                  <span
                    className={cn(
                      'whitespace-nowrap transition-opacity duration-150',
                      isExpanded ? 'opacity-100' : 'opacity-0 hidden'
                    )}
                  >
                    {item.name}
                  </span>
                </Link>
              )

              return isExpanded ? linkElement : (
                <Tooltip key={item.name} delayDuration={0}>
                  <TooltipTrigger asChild>
                    {linkElement}
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.name}
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </nav>

          <Separator className="my-4" />

          {/* Secondary Navigation */}
          <nav className="space-y-1 px-2">
            {secondaryNavigation.map((item) => {
              const isActive = pathname === item.href
              const Icon = item.icon

              const linkElement = (
                <Link
                  href={item.href}
                  className={cn(
                    'flex h-9 items-center rounded-md px-3 text-sm transition-colors',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isExpanded ? 'justify-start gap-3' : 'justify-center'
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {/* Text - Hidden when collapsed */}
                  <span
                    className={cn(
                      'whitespace-nowrap transition-opacity duration-150',
                      isExpanded ? 'opacity-100' : 'opacity-0 hidden'
                    )}
                  >
                    {item.name}
                  </span>
                </Link>
              )

              return isExpanded ? linkElement : (
                <Tooltip key={item.name} delayDuration={0}>
                  <TooltipTrigger asChild>
                    {linkElement}
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.name}
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </nav>
        </ScrollArea>
      </div>
    </aside>
  )
}
