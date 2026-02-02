import { RuleExecutionResponse } from './api'

export interface DMNUploadResponse {
  filename: string
  file_path: string
  rules: any[]
  patterns: Record<string, string>
  rules_count: number
  correlation_id?: string
}

export interface DMNRuleExecutionRequest {
  dmn_file?: string
  dmn_content?: string
  data: Record<string, any>
  dry_run?: boolean
  correlation_id?: string
}

export type DMNExecutionResponse = RuleExecutionResponse
