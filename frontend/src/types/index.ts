import { RuleExecutionResponse, BatchRuleExecutionResponse, WorkflowExecutionResponse } from './api'

export type ExecutionType = 'single' | 'batch' | 'workflow' | 'dmn'

export interface ExecutionRecord {
  id: string
  type: ExecutionType
  timestamp: string
  data_summary: string
  status: 'success' | 'failed'
  result?: RuleExecutionResponse | BatchRuleExecutionResponse | WorkflowExecutionResponse
  correlation_id?: string
  error?: string
}

export * from './api'
export * from './rule'
export * from './condition'
export * from './action'
export * from './ruleset'
export * from './workflow'
export * from './dmn'
