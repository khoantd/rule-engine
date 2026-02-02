import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ExecutionRecord } from '@/types'

interface ExecutionState {
  history: ExecutionRecord[]
  currentExecution: ExecutionRecord | null
  maxHistorySize: number

  actions: {
    addToHistory: (execution: ExecutionRecord) => void
    removeFromHistory: (id: string) => void
    clearHistory: () => void
    setCurrentExecution: (execution: ExecutionRecord | null) => void
    getHistoryByType: (type: ExecutionRecord['type']) => ExecutionRecord[]
  }
}

export const useExecutionStore = create<ExecutionState>()(
  persist(
    (set, get) => ({
      history: [],
      currentExecution: null,
      maxHistorySize: 100,

      actions: {
        addToHistory: (execution) =>
          set((state) => {
            const newHistory = [execution, ...state.history].slice(
              0,
              state.maxHistorySize,
            )
            return { history: newHistory }
          }),

        removeFromHistory: (id) =>
          set((state) => ({
            history: state.history.filter((exec) => exec.id !== id),
          })),

        clearHistory: () => set({ history: [] }),

        setCurrentExecution: (execution) => set({ currentExecution: execution }),

        getHistoryByType: (type) =>
          get().history.filter((exec) => exec.type === type),
      },
    }),
    {
      name: 'execution-storage',
    },
  ),
)
