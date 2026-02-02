import { api } from './api'
import { HealthResponse } from '@/types/api'

export const healthService = {
  check: async (): Promise<HealthResponse> => {
    const response = await api.get<HealthResponse>('/health')
    return response.data
  },

  getInfo: async () => {
    const response = await api.get('/')
    return response.data
  },
}
