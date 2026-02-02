import { useMutation } from '@tanstack/react-query'
import { workflowService } from '@/services'
import type { WorkflowExecutionRequest } from '@/types/workflow'
import { useExecutionStore } from '@/stores'
import { ExecutionRecord } from '@/types'

export const useExecuteWorkflow = () => {
  const addToHistory = useExecutionStore((state) => state.actions.addToHistory)

  return useMutation({
    mutationFn: (data: WorkflowExecutionRequest) => workflowService.execute(data),
    onSuccess: (result, variables: WorkflowExecutionRequest) => {
      const record: ExecutionRecord = {
        id: `workflow-${Date.now()}`,
        type: 'workflow',
        timestamp: new Date().toISOString(),
        data_summary: `${variables.process_name} (${variables.stages.length} stages)`,
        status: 'success',
        result,
        correlation_id: result.process_name,
      }
      addToHistory(record)
    },
  })
}
