import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rulesService } from '@/services'
import type { RuleCreateRequest, RuleUpdateRequest } from '@/types/rule'

export const useRules = () => {
  return useQuery({
    queryKey: ['rules'],
    queryFn: () => rulesService.getAll(),
  })
}

export const useRule = (id: string) => {
  return useQuery({
    queryKey: ['rules', id],
    queryFn: () => rulesService.getById(id),
    enabled: !!id,
  })
}

export const useCreateRule = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: RuleCreateRequest) => rulesService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })
}

export const useUpdateRule = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RuleUpdateRequest }) =>
      rulesService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })
}

export const useDeleteRule = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => rulesService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })
}
