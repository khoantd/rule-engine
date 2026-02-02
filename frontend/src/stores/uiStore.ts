import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Toast {
  id: string
  title: string
  description?: string
  variant?: 'default' | 'destructive' | 'success'
  duration?: number
}

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  toasts: Toast[]
  currentModal: string | null

  actions: {
    toggleSidebar: () => void
    setSidebarOpen: (open: boolean) => void
    setTheme: (theme: 'light' | 'dark') => void
    addToast: (toast: Omit<Toast, 'id'>) => void
    removeToast: (id: string) => void
    clearToasts: () => void
    openModal: (modal: string) => void
    closeModal: () => void
  }
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      theme: 'light',
      toasts: [],
      currentModal: null,

      actions: {
        toggleSidebar: () =>
          set((state) => ({
            sidebarOpen: !state.sidebarOpen,
          })),

        setSidebarOpen: (open) => set({ sidebarOpen: open }),

        setTheme: (theme) => set({ theme }),

        addToast: (toast) => {
          const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          set((state) => ({
            toasts: [...state.toasts, { ...toast, id }],
          }))

          const duration = toast.duration ?? 5000
          setTimeout(() => {
            get().actions.removeToast(id)
          }, duration)
        },

        removeToast: (id) =>
          set((state) => ({
            toasts: state.toasts.filter((toast) => toast.id !== id),
          })),

        clearToasts: () => set({ toasts: [] }),

        openModal: (modal) => set({ currentModal: modal }),

        closeModal: () => set({ currentModal: null }),
      },
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        theme: state.theme,
      }),
    },
  ),
)
