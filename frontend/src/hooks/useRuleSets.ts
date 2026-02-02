import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rulesetsService } from '@/services'
import type { RuleSetCreateRequest, RuleSetUpdateRequest } from '@/types/ruleset'

export const useRuleSets = () => {
  return useQuery({
    queryKey: ['rulesets'],
    queryFn: () => rulesetsService.getAll(),
  })
}

export const useRuleSet = (name: string) => {
  return useQuery({
    queryKey: ['rulesets', name],
    queryFn: () => rulesetsService.getByName(name),
    enabled: !!name,
  })
}

export const useCreateRuleSet = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: RuleSetCreateRequest) => rulesetsService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}

export const useUpdateRuleSet = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, data }: { name: string; data: RuleSetUpdateRequest }) =>
      rulesetsService.update(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}

export const useDeleteRuleSet = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (name: string) => rulesetsService.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}
