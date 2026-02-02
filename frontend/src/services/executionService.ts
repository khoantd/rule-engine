import { api } from './api'
import {
  RuleExecutionRequest,
  RuleExecutionResponse,
  BatchRuleExecutionRequest,
  BatchRuleExecutionResponse,
} from '@/types/api'

export const executionService = {
  executeSingle: async (data: RuleExecutionRequest): Promise<RuleExecutionResponse> => {
    const response = await api.post<RuleExecutionResponse>('/api/v1/rules/execute', data)
    return response.data
  },

  executeBatch: async (
    data: BatchRuleExecutionRequest,
  ): Promise<BatchRuleExecutionResponse> => {
    const response = await api.post<BatchRuleExecutionResponse>('/api/v1/rules/batch', data)
    return response.data
  },
}
