'use client'

import { useEffect, useState } from 'react'
import { useUIStore } from '@/stores'

const Toaster = () => {
  const [mounted, setMounted] = useState(false)
  const { toasts, actions } = useUIStore()

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  return (
    <div className="fixed top-0 right-0 z-50 flex flex-col gap-2 p-4 max-w-sm w-full">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'p-4 rounded-lg shadow-lg border transition-all duration-300',
            toast.variant === 'default' && 'bg-background border-border',
            toast.variant === 'destructive' && 'bg-destructive text-destructive-foreground border-destructive',
            toast.variant === 'success' && 'bg-green-50 text-green-900 border-green-500 dark:bg-green-950 dark:text-green-100',
          )}
          role="alert"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <p className="font-semibold text-sm">{toast.title}</p>
              {toast.description && (
                <p className="text-sm opacity-90 mt-1">{toast.description}</p>
              )}
            </div>
            <button
              onClick={() => actions.removeToast(toast.id)}
              className="text-current opacity-70 hover:opacity-100 transition-opacity"
              aria-label="Close toast"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}

export { Toaster }
