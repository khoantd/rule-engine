import { api } from './api'
import {
  ConditionsListResponse,
  ConditionCreateRequest,
  ConditionUpdateRequest,
} from '@/types/condition'

export const conditionsService = {
  getAll: async (): Promise<ConditionsListResponse> => {
    const response = await api.get<ConditionsListResponse>('/api/v1/conditions')
    return response.data
  },

  getById: async (id: string) => {
    const response = await api.get(`/api/v1/conditions/${id}`)
    return response.data
  },

  create: async (data: ConditionCreateRequest) => {
    const response = await api.post('/api/v1/conditions', data)
    return response.data
  },

  update: async (id: string, data: ConditionUpdateRequest) => {
    const response = await api.put(`/api/v1/conditions/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await api.delete(`/api/v1/conditions/${id}`)
    return id
  },
}
