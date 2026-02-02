import type { WorkflowExecutionRequest, WorkflowExecutionResponse } from './api'

export interface WorkflowStage {
  name: string
  handler?: string
  config?: Record<string, any>
}

export interface Workflow {
  process_name: string
  stages: WorkflowStage[]
}

export type WorkflowRequest = WorkflowExecutionRequest
export type WorkflowResponse = WorkflowExecutionResponse
