import { api } from './api'
import {
  RulesListResponse,
  RuleCreateRequest,
  RuleUpdateRequest,
} from '@/types/rule'

export const rulesService = {
  getAll: async (): Promise<RulesListResponse> => {
    const response = await api.get<RulesListResponse>('/api/v1/rules')
    return response.data
  },

  getById: async (id: string) => {
    const response = await api.get(`/api/v1/rules/${id}`)
    return response.data
  },

  create: async (data: RuleCreateRequest) => {
    const response = await api.post('/api/v1/rules', data)
    return response.data
  },

  update: async (id: string, data: RuleUpdateRequest) => {
    const response = await api.put(`/api/v1/rules/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await api.delete(`/api/v1/rules/${id}`)
    return id
  },
}
