import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { actionsService } from '@/services'
import type { ActionCreateRequest, ActionUpdateRequest } from '@/types/action'

export const useActions = () => {
  return useQuery({
    queryKey: ['actions'],
    queryFn: () => actionsService.getAll(),
  })
}

export const useAction = (pattern: string) => {
  return useQuery({
    queryKey: ['actions', pattern],
    queryFn: () => actionsService.getByPattern(pattern),
    enabled: !!pattern,
  })
}

export const useCreateAction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ActionCreateRequest) => actionsService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}

export const useUpdateAction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ pattern, data }: { pattern: string; data: ActionUpdateRequest }) =>
      actionsService.update(pattern, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}

export const useDeleteAction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (pattern: string) => actionsService.delete(pattern),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}
