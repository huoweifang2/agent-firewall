import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { api } from '~/services/api'
import type {
  OpenClawAgentsResponse,
  OpenClawHooksResponse,
  OpenClawSkillsResponse,
  OpenClawStatusResponse,
  ToolCreate,
  ToolRead,
  ToolUpdate,
} from '~/types/agentControl'

export const useAgentTools = (agentId: () => string) => {
  const queryClient = useQueryClient()

  const queryKey = computed(() => ['agent-control-tools', agentId()])

  const { data: tools, isLoading, error, refetch } = useQuery<ToolRead[]>({
    queryKey,
    queryFn: () =>
      api.get<ToolRead[]>(`/v1/agents/${agentId()}/tools`).then(r => r.data),
    staleTime: 0,
    enabled: () => !!agentId(),
  })

  const createMutation = useMutation({
    mutationFn: (body: ToolCreate) =>
      api.post<ToolRead>(`/v1/agents/${agentId()}/tools`, body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.value })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ toolId, body }: { toolId: string; body: ToolUpdate }) =>
      api.patch<ToolRead>(`/v1/agents/${agentId()}/tools/${toolId}`, body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.value })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (toolId: string) =>
      api.delete(`/v1/agents/${agentId()}/tools/${toolId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.value })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  const importOpenClawMutation = useMutation({
    mutationFn: (skills: string[]) =>
      api.post<ToolRead[]>(`/v1/agents/${agentId()}/tools/openclaw/import`, { skills }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.value })
      queryClient.invalidateQueries({ queryKey: ['agent-runtime-spec'] })
    },
  })

  return {
    tools: computed(() => tools.value ?? []),
    isLoading,
    error,
    refetch,
    createTool: createMutation.mutateAsync,
    updateTool: updateMutation.mutateAsync,
    deleteTool: deleteMutation.mutateAsync,
    importOpenClawTools: importOpenClawMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isImportingOpenClaw: importOpenClawMutation.isPending,
  }
}

export const useOpenClawSkills = () => useQuery<OpenClawSkillsResponse>({
  queryKey: ['openclaw-skills'],
  queryFn: () => api.get<OpenClawSkillsResponse>('/v1/openclaw/skills', {
    params: { eligible_only: true },
  }).then(r => r.data),
  staleTime: 60_000,
})

export const useOpenClawAgents = () => useQuery<OpenClawAgentsResponse>({
  queryKey: ['openclaw-agents'],
  queryFn: () => api.get<OpenClawAgentsResponse>('/v1/openclaw/agents').then(r => r.data),
  staleTime: 30_000,
})

export const useOpenClawHooks = () => useQuery<OpenClawHooksResponse>({
  queryKey: ['openclaw-hooks'],
  queryFn: () => api.get<OpenClawHooksResponse>('/v1/openclaw/hooks').then(r => r.data),
  staleTime: 30_000,
})

export const useOpenClawStatus = () => useQuery<OpenClawStatusResponse>({
  queryKey: ['openclaw-status'],
  queryFn: () => api.get<OpenClawStatusResponse>('/v1/openclaw/status').then(r => r.data),
  staleTime: 30_000,
})
