import { useQuery } from '@tanstack/vue-query'
import { computed, type Ref } from 'vue'
import { api } from '~/services/api'
import type { TraceRunDetail, TraceRunListResponse } from '~/types/agentTraceRun'

export interface AgentTraceRunFilters {
  sessionId?: Ref<string | null>
  userRole?: Ref<string | null>
  hasBlocks?: Ref<boolean | null>
  dateFrom?: Ref<string | null>
  dateTo?: Ref<string | null>
  page?: Ref<number>
  pageSize?: Ref<number>
}

export function useAgentTraceRuns(agentId: () => string, filters?: AgentTraceRunFilters) {
  const queryKey = computed(() => [
    'agent-trace-runs',
    agentId(),
    filters?.sessionId?.value,
    filters?.userRole?.value,
    filters?.hasBlocks?.value,
    filters?.dateFrom?.value,
    filters?.dateTo?.value,
    filters?.page?.value ?? 1,
    filters?.pageSize?.value ?? 25,
  ])

  const query = useQuery<TraceRunListResponse>({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams()
      const page = filters?.page?.value ?? 1
      const pageSize = filters?.pageSize?.value ?? 25
      params.set('limit', String(pageSize))
      params.set('offset', String((page - 1) * pageSize))
      if (filters?.sessionId?.value) params.set('session_id', filters.sessionId.value)
      if (filters?.userRole?.value) params.set('user_role', filters.userRole.value)
      if (filters?.hasBlocks?.value != null) params.set('has_blocks', String(filters.hasBlocks.value))
      if (filters?.dateFrom?.value) params.set('from', filters.dateFrom.value)
      if (filters?.dateTo?.value) params.set('to', filters.dateTo.value)
      return api.get<TraceRunListResponse>(`/v1/agents/${agentId()}/traces/runs?${params}`).then(r => r.data)
    },
    enabled: () => !!agentId(),
    placeholderData: (prev) => prev,
    staleTime: 0,
  })

  const fetchDetail = (traceId: string) =>
    api.get<TraceRunDetail>(`/v1/agents/${agentId()}/traces/runs/${traceId}`).then(r => r.data)

  return {
    items: computed(() => query.data.value?.items ?? []),
    total: computed(() => query.data.value?.total ?? 0),
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    fetchDetail,
    fetchExport: fetchDetail,
  }
}

