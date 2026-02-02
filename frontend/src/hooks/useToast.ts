import { useUIStore } from '@/stores'

export const useToast = () => {
  const { actions } = useUIStore()

  const addToast = (
    title: string,
    description?: string,
    variant: 'default' | 'destructive' | 'success' = 'default',
    duration?: number,
  ) => {
    actions.addToast({ title, description, variant, duration })
  }

  const success = (title: string, description?: string, duration?: number) => {
    addToast(title, description, 'success', duration)
  }

  const error = (title: string, description?: string, duration?: number) => {
    addToast(title, description, 'destructive', duration)
  }

  const info = (title: string, description?: string, duration?: number) => {
    addToast(title, description, 'default', duration)
  }

  return {
    addToast,
    success,
    error,
    info,
  }
}
