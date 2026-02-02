import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { conditionsService } from '@/services'
import type { ConditionCreateRequest, ConditionUpdateRequest } from '@/types/condition'

export const useConditions = () => {
  return useQuery({
    queryKey: ['conditions'],
    queryFn: () => conditionsService.getAll(),
  })
}

export const useCondition = (id: string) => {
  return useQuery({
    queryKey: ['conditions', id],
    queryFn: () => conditionsService.getById(id),
    enabled: !!id,
  })
}

export const useCreateCondition = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ConditionCreateRequest) => conditionsService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conditions'] })
    },
  })
}

export const useUpdateCondition = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ConditionUpdateRequest }) =>
      conditionsService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conditions'] })
    },
  })
}

export const useDeleteCondition = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => conditionsService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conditions'] })
    },
  })
}
