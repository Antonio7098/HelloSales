'use client'

import * as React from 'react'
import { useSidebar } from '@/hooks/use-sidebar'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { CommandPalette } from '@/components/command-palette'
import { cn } from '@/lib/utils'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { hovered } = useSidebar()
  const isExpanded = hovered

  return (
    <div className="min-h-screen">
      <Sidebar />
      <Header />
      <main
        className={cn(
          'pt-16 transition-all duration-200',
          isExpanded ? 'ml-[260px]' : 'ml-[60px]'
        )}
      >
        <div className="p-6">{children}</div>
      </main>
      <CommandPalette />
    </div>
  )
}
