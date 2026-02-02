import { api } from './api'
import {
  ActionsListResponse,
  ActionCreateRequest,
  ActionUpdateRequest,
} from '@/types/action'

export const actionsService = {
  getAll: async (): Promise<ActionsListResponse> => {
    const response = await api.get<ActionsListResponse>('/api/v1/actions')
    return response.data
  },

  getByPattern: async (pattern: string) => {
    const response = await api.get(`/api/v1/actions/${pattern}`)
    return response.data
  },

  create: async (data: ActionCreateRequest) => {
    const response = await api.post('/api/v1/actions', data)
    return response.data
  },

  update: async (pattern: string, data: ActionUpdateRequest) => {
    const response = await api.put(`/api/v1/actions/${pattern}`, data)
    return response.data
  },

  delete: async (pattern: string) => {
    await api.delete(`/api/v1/actions/${pattern}`)
    return pattern
  },
}
