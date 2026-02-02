import { api } from './api'
import {
  RuleSetsListResponse,
  RuleSetCreateRequest,
  RuleSetUpdateRequest,
} from '@/types/ruleset'

export const rulesetsService = {
  getAll: async (): Promise<RuleSetsListResponse> => {
    const response = await api.get<RuleSetsListResponse>('/api/v1/rulesets')
    return response.data
  },

  getByName: async (name: string) => {
    const response = await api.get(`/api/v1/rulesets/${name}`)
    return response.data
  },

  create: async (data: RuleSetCreateRequest) => {
    const response = await api.post('/api/v1/rulesets', data)
    return response.data
  },

  update: async (name: string, data: RuleSetUpdateRequest) => {
    const response = await api.put(`/api/v1/rulesets/${name}`, data)
    return response.data
  },

  delete: async (name: string) => {
    await api.delete(`/api/v1/rulesets/${name}`)
    return name
  },
}
