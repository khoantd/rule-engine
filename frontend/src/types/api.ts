import { z } from 'zod'

export interface RuleEvaluationResult {
  rule_name: string
  rule_priority?: number
  condition: string
  matched: boolean
  action_result: string
  rule_point: number
  weight: number
  execution_time_ms: number
}

export interface RuleExecutionResponse {
  total_points: number
  pattern_result: string
  action_recommendation?: string
  decision_outputs?: Record<string, any>
  rule_evaluations?: RuleEvaluationResult[]
  would_match?: RuleEvaluationResult[]
  would_not_match?: RuleEvaluationResult[]
  dry_run?: boolean
  execution_time_ms?: number
  correlation_id?: string
}

export interface BatchItemResult {
  item_index: number
  correlation_id: string
  status: string
  total_points?: number
  pattern_result?: string
  action_recommendation?: string
  error?: string
  error_type?: string
}

export interface BatchRuleExecutionResponse {
  batch_id: string
  results: BatchItemResult[]
  summary: {
    total_executions: number
    successful_executions: number
    failed_executions: number
    total_execution_time_ms: number
    avg_execution_time_ms: number
    success_rate: number
  }
  dry_run?: boolean
}

export interface WorkflowExecutionResponse {
  process_name: string
  stages: string[]
  result?: Record<string, any>
  execution_time_ms?: number
}

export interface HealthResponse {
  status: string
  version: string
  timestamp: string
  uptime_seconds?: number
  environment?: string
}

export interface ErrorResponse {
  error_type: string
  message: string
  error_code?: string
  context?: Record<string, any>
  correlation_id?: string
}

export interface ApiResponse<T> {
  data?: T
  error?: ErrorResponse
  correlation_id?: string
}

export const RuleExecutionRequestSchema = z.object({
  data: z.record(z.any()),
  dry_run: z.boolean().optional().default(false),
  correlation_id: z.string().optional(),
})

export const BatchRuleExecutionRequestSchema = z.object({
  data_list: z.array(z.record(z.any())).min(1),
  dry_run: z.boolean().optional().default(false),
  max_workers: z.number().positive().optional(),
  correlation_id: z.string().optional(),
})

export const WorkflowExecutionRequestSchema = z.object({
  process_name: z.string().min(1),
  stages: z.array(z.string()).optional().default(['NEW', 'INPROGESS', 'FINISHED']),
  data: z.record(z.any()).optional().default({}),
})

export type RuleExecutionRequest = z.infer<typeof RuleExecutionRequestSchema>
export type BatchRuleExecutionRequest = z.infer<typeof BatchRuleExecutionRequestSchema>
export type WorkflowExecutionRequest = z.infer<typeof WorkflowExecutionRequestSchema>
