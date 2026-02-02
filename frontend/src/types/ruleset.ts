import { z } from 'zod'

export interface RuleSet {
  ruleset_name: string
  rules: Record<string, any>[]
  actionset: string[]
}

export interface RuleSetsListResponse {
  rulesets: RuleSet[]
  count: number
}

export const RuleSetCreateRequestSchema = z.object({
  ruleset_name: z.string().min(1),
  rules: z.array(z.union([z.string(), z.record(z.any())])).optional().default([]),
  actionset: z.array(z.union([z.string(), z.record(z.any())])).optional().default([]),
})

export const RuleSetUpdateRequestSchema = RuleSetCreateRequestSchema.partial().omit({
  ruleset_name: true,
})

export type RuleSetCreateRequest = z.infer<typeof RuleSetCreateRequestSchema>
export type RuleSetUpdateRequest = z.infer<typeof RuleSetUpdateRequestSchema>
