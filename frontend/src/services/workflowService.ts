import { api } from './api'
import {
  WorkflowExecutionRequest,
  WorkflowExecutionResponse,
} from '@/types/workflow'

export const workflowService = {
  execute: async (
    data: WorkflowExecutionRequest,
  ): Promise<WorkflowExecutionResponse> => {
    const response = await api.post<WorkflowExecutionResponse>('/api/v1/workflow/execute', data)
    return response.data
  },
}
