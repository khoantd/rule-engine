import { useMutation } from '@tanstack/react-query'
import { executionService } from '@/services'
import type {
  RuleExecutionRequest,
  RuleExecutionResponse,
  BatchRuleExecutionRequest,
  BatchRuleExecutionResponse,
} from '@/types/api'
import { useExecutionStore } from '@/stores'
import { ExecutionRecord } from '@/types'

export const useExecuteSingle = () => {
  const addToHistory = useExecutionStore((state) => state.actions.addToHistory)

  return useMutation({
    mutationFn: (data: RuleExecutionRequest) => executionService.executeSingle(data),
    onSuccess: (result: RuleExecutionResponse, variables: RuleExecutionRequest) => {
      const record: ExecutionRecord = {
        id: `exec-${Date.now()}`,
        type: 'single',
        timestamp: new Date().toISOString(),
        data_summary: JSON.stringify(variables.data).substring(0, 100),
        status: 'success',
        result,
        correlation_id: result.correlation_id,
      }
      addToHistory(record)
    },
  })
}

export const useExecuteBatch = () => {
  const addToHistory = useExecutionStore((state) => state.actions.addToHistory)

  return useMutation({
    mutationFn: (data: BatchRuleExecutionRequest) =>
      executionService.executeBatch(data),
    onSuccess: (result: BatchRuleExecutionResponse, variables: BatchRuleExecutionRequest) => {
      const record: ExecutionRecord = {
        id: result.batch_id,
        type: 'batch',
        timestamp: new Date().toISOString(),
        data_summary: `${variables.data_list.length} items`,
        status: result.summary.success_rate === 100 ? 'success' : 'failed',
        result,
        correlation_id: result.batch_id,
      }
      addToHistory(record)
    },
  })
}
