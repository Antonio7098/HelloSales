'use client'

import * as React from 'react'
import { Command } from 'cmdk'
import { Search, ImageIcon, Users, Palette, Building2, Briefcase } from 'lucide-react'
import { useRouter } from 'next/navigation'

export function CommandPalette() {
  const [open, setOpen] = React.useState(false)
  const router = useRouter()

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const runCommand = React.useCallback((command: () => unknown) => {
    setOpen(false)
    command()
  }, [])

  return (
    <>
      {/* Trigger hint in header */}
      <Command.Dialog
        open={open}
        onOpenChange={setOpen}
        label="Global Command Menu"
        className="fixed top-1/2 left-1/2 w-full max-w-[640px] -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-popover p-2 shadow-lg shadow-black/50 backdrop-blur-xl open:animate-in closed:animate-out fade-in-0 zoom-in-95 fade-out-0 zoom-out-95"
      >
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
          <Command.Input
            placeholder="Type a command or search..."
            className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
        <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-2">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="text-xs text-muted-foreground mb-2">
            <Command.Item
              onSelect={() => runCommand(() => router.push('/'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Palette className="mr-2 h-4 w-4" />
              <span>Dashboard</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => router.push('/artworks'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <ImageIcon className="mr-2 h-4 w-4" />
              <span>Artworks</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => router.push('/artists'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Users className="mr-2 h-4 w-4" />
              <span>Artists</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => router.push('/exhibitions'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Palette className="mr-2 h-4 w-4" />
              <span>Exhibitions</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => router.push('/collections'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Building2 className="mr-2 h-4 w-4" />
              <span>Collections</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => router.push('/partners'))}
              className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Briefcase className="mr-2 h-4 w-4" />
              <span>Partners</span>
            </Command.Item>
          </Command.Group>
        </Command.List>
      </Command.Dialog>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50"
          onClick={() => setOpen(false)}
        />
      )}
    </>
  )
}
