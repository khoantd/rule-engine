import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface FormState {
  drafts: Record<string, any>

  actions: {
    saveDraft: (key: string, data: any) => void
    loadDraft: (key: string) => any | null
    clearDraft: (key: string) => void
    clearAllDrafts: () => void
  }
}

export const useFormStore = create<FormState>()(
  persist(
    (set, get) => ({
      drafts: {},

      actions: {
        saveDraft: (key, data) =>
          set((state) => ({
            drafts: { ...state.drafts, [key]: { data, timestamp: Date.now() } },
          })),

        loadDraft: (key) => {
          const draft = get().drafts[key]
          if (!draft) return null

          const age = Date.now() - (draft.timestamp ?? 0)
          const maxAge = 24 * 60 * 60 * 1000 // 24 hours

          if (age > maxAge) {
            get().actions.clearDraft(key)
            return null
          }

          return draft.data
        },

        clearDraft: (key) =>
          set((state) => {
            const { [key]: _, ...rest } = state.drafts
            return { drafts: rest }
          }),

        clearAllDrafts: () => set({ drafts: {} }),
      },
    }),
    {
      name: 'form-storage',
    },
  ),
)
