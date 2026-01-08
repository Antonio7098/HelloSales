import { create } from 'zustand'

interface SidebarState {
  collapsed: boolean
  hovered: boolean
  toggle: () => void
  setCollapsed: (collapsed: boolean) => void
  setHovered: (hovered: boolean) => void
}

export const useSidebar = create<SidebarState>((set) => ({
  collapsed: true,
  hovered: false,
  toggle: () => set((state) => ({ collapsed: !state.collapsed })),
  setCollapsed: (collapsed) => set({ collapsed }),
  setHovered: (hovered) => set({ hovered }),
}))
