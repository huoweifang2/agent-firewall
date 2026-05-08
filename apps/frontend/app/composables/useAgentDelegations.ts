import { computed } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api } from '~/services/api'
import type { DelegationCreate, DelegationRead } from '~/types/agentControl'

export function useAgentDelegations(agentId: () => string) {
  const queryClient = useQueryClient()
  const queryKey = computed(() => ['agent-delegations', agentId()])

  const query = useQuery<DelegationRead[]>({
    queryKey,
    queryFn: () => api.get<DelegationRead[]>(`/v1/agents/${agentId()}/sub-agents`).then(r => r.data),
    enabled: () => !!agentId(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ bindingId, body }: { bindingId: string; body: Partial<DelegationRead> }) =>
      api.patch<DelegationRead>(`/v1/agents/${agentId()}/sub-agents/${bindingId}`, body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-delegations'] })
      queryClient.invalidateQueries({ queryKey: ['agent-teams'] })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: (body: DelegationCreate) =>
      api.post<DelegationRead>(`/v1/agents/${agentId()}/sub-agents`, body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-delegations'] })
      queryClient.invalidateQueries({ queryKey: ['agent-teams'] })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (bindingId: string) =>
      api.delete(`/v1/agents/${agentId()}/sub-agents/${bindingId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-delegations'] })
      queryClient.invalidateQueries({ queryKey: ['agent-teams'] })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  return {
    delegations: computed(() => query.data.value ?? []),
    isLoading: query.isLoading,
    refetch: query.refetch,
    createDelegation: createMutation.mutateAsync,
    updateDelegation: updateMutation.mutateAsync,
    deleteDelegation: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}
