import { z } from 'zod'

export interface Rule {
  id: string
  rule_name: string
  type?: string
  conditions: Record<string, any>
  description: string
  result: string
  weight?: number
  rule_point?: number
  priority?: number
  action_result?: string
}

export interface RulesListResponse {
  rules: Rule[]
  count: number
}

export const RuleCreateRequestSchema = z.object({
  id: z.string().min(1),
  rule_name: z.string().min(1),
  type: z.enum(['simple', 'complex']).optional().default('simple'),
  conditions: z.record(z.any()),
  description: z.string().min(1),
  result: z.string().min(1),
  weight: z.number().optional(),
  rule_point: z.number().optional(),
  priority: z.number().int().optional(),
  action_result: z.string().optional(),
})

export const RuleUpdateRequestSchema = RuleCreateRequestSchema.partial().omit({ id: true })

export type RuleCreateRequest = z.infer<typeof RuleCreateRequestSchema>
export type RuleUpdateRequest = z.infer<typeof RuleUpdateRequestSchema>
