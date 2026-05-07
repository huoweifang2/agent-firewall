import { computed, type Ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '~/services/api'
import type { AgentRuntimeSpec } from '~/types/agentControl'

export function useAgentRuntimeSpec(agentId: Ref<string | null | undefined>) {
  const query = useQuery<AgentRuntimeSpec>({
    queryKey: computed(() => ['agent-runtime-spec', agentId.value ?? null]),
    enabled: computed(() => Boolean(agentId.value)),
    queryFn: async () => {
      const id = agentId.value
      if (!id) {
        throw new Error('Agent ID is required')
      }
      const { data } = await api.get<AgentRuntimeSpec>(`/v1/agents/${id}/runtime-spec`)
      return data
    },
    staleTime: 15_000,
  })

  return {
    runtimeSpec: computed(() => query.data.value ?? null),
    roles: computed(() => query.data.value?.roles ?? []),
    tools: computed(() => query.data.value?.tools ?? []),
    skills: computed(() => query.data.value?.skills ?? []),
    subAgents: computed(() => query.data.value?.sub_agents ?? []),
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  }
}
