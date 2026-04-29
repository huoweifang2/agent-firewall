import { computed } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api } from '~/services/api'
import type {
  AgentTeamRead,
  AgentTeamsResponse,
  AgentTeamTemplateCreate,
  DelegationRead,
  SubAgentCreateRequest,
} from '~/types/wizard'

export function useAgentTeams() {
  const queryClient = useQueryClient()

  const query = useQuery<AgentTeamsResponse>({
    queryKey: ['agent-teams'],
    queryFn: () => api.get<AgentTeamsResponse>('/v1/agent-teams').then(r => r.data),
    staleTime: 10_000,
  })

  const createSubAgentMutation = useMutation({
    mutationFn: ({ mainAgentId, body }: { mainAgentId: string; body: SubAgentCreateRequest }) =>
      api.post<DelegationRead>(`/v1/agents/${mainAgentId}/sub-agents/create`, body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-teams'] })
      queryClient.invalidateQueries({ queryKey: ['wizard-agents'] })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const createTemplateMutation = useMutation({
    mutationFn: (body: AgentTeamTemplateCreate) =>
      api.post<AgentTeamRead>('/v1/agent-team-templates', body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-teams'] })
      queryClient.invalidateQueries({ queryKey: ['wizard-agents'] })
    },
  })

  return {
    teams: computed(() => query.data.value?.items ?? []),
    total: computed(() => query.data.value?.total ?? 0),
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    createSubAgent: createSubAgentMutation.mutateAsync,
    isCreatingSubAgent: createSubAgentMutation.isPending,
    createTemplate: createTemplateMutation.mutateAsync,
    isCreatingTemplate: createTemplateMutation.isPending,
  }
}
