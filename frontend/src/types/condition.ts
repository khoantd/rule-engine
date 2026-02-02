import { z } from 'zod'

export interface Condition {
  condition_id: string
  condition_name: string
  attribute: string
  equation: string
  constant: string | number | string[]
}

export interface ConditionsListResponse {
  conditions: Condition[]
  count: number
}

export const ConditionCreateRequestSchema = z.object({
  condition_id: z.string().min(1),
  condition_name: z.string().min(1),
  attribute: z.string().min(1),
  equation: z.enum([
    'equal',
    'not_equal',
    'greater_than',
    'greater_than_or_equal',
    'less_than',
    'less_than_or_equal',
    'in',
    'not_in',
    'range',
    'contains',
    'regex',
  ]),
  constant: z.union([z.string(), z.number(), z.array(z.string())]),
})

export const ConditionUpdateRequestSchema = ConditionCreateRequestSchema.partial().omit({
  condition_id: true,
})

export type ConditionCreateRequest = z.infer<typeof ConditionCreateRequestSchema>
export type ConditionUpdateRequest = z.infer<typeof ConditionUpdateRequestSchema>
