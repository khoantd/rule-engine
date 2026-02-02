import { z } from 'zod'

export interface Action {
  pattern: string
  message: string
}

export interface ActionsListResponse {
  actions: Record<string, string>
  count: number
}

export const ActionCreateRequestSchema = z.object({
  pattern: z.string().min(1),
  message: z.string().min(1),
})

export const ActionUpdateRequestSchema = z.object({
  message: z.string().min(1),
})

export type ActionCreateRequest = z.infer<typeof ActionCreateRequestSchema>
export type ActionUpdateRequest = z.infer<typeof ActionUpdateRequestSchema>
