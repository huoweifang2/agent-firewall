import { computed } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api } from '~/services/api'
import type { DelegationRead } from '~/types/agentControl'

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

  return {
    delegations: computed(() => query.data.value ?? []),
    isLoading: query.isLoading,
    refetch: query.refetch,
    updateDelegation: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  }
}
