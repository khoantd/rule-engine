import { api } from './api'
import { DMNUploadResponse, DMNRuleExecutionRequest, DMNExecutionResponse } from '@/types/dmn'

export const dmnService = {
  upload: async (file: File): Promise<DMNUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<DMNUploadResponse>('/api/v1/dmn/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  execute: async (data: DMNRuleExecutionRequest): Promise<DMNExecutionResponse> => {
    const response = await api.post<DMNExecutionResponse>('/api/v1/rules/execute-dmn', data)
    return response.data
  },

  executeWithUpload: async (
    file: File,
    data: Record<string, any>,
    dryRun?: boolean,
  ): Promise<DMNExecutionResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('data', JSON.stringify(data))
    if (dryRun !== undefined) {
      formData.append('dry_run', String(dryRun))
    }

    const response = await api.post<DMNExecutionResponse>(
      '/api/v1/rules/execute-dmn-upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      },
    )
    return response.data
  },
}
