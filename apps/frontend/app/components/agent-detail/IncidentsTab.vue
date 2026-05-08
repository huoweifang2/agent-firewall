<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex align-center justify-space-between mb-3">
      <div>
        <h3 class="text-subtitle-1">Incidents</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Persistent incident groups, with trace-run guidance when only runtime evidence exists.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-select v-model="status" :items="statusItems" label="Status" density="compact" variant="outlined" clearable hide-details style="width: 170px" />
        <v-btn size="small" variant="text" icon="mdi-refresh" :loading="isLoading || tracesLoading" @click="refreshAll" />
      </div>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <v-data-table
      v-if="incidents.length"
      :headers="headers"
      :items="incidents"
      :items-per-page="20"
      density="compact"
    >
      <template #item.severity="{ item }">
        <v-chip :color="severityColor(item.severity)" size="x-small" variant="tonal">{{ item.severity }}</v-chip>
      </template>
      <template #item.status="{ item }">
        <v-chip v-if="item.details?.synthetic" size="x-small" color="warning" variant="tonal">
          trace-run evidence
        </v-chip>
        <v-select
          v-else
          :model-value="item.status"
          :items="statusItems"
          variant="plain"
          density="compact"
          hide-details
          style="max-width: 170px"
          @update:model-value="(value: string | null) => value && updateStatus(item.id, value)"
        />
      </template>
      <template #item.first_seen="{ item }">
        {{ new Date(item.first_seen).toLocaleString() }}
      </template>
    </v-data-table>

    <v-card v-else-if="blockedRuns.length" variant="tonal" color="warning" class="pa-4">
      <div class="d-flex align-start ga-3">
        <v-icon icon="mdi-alert-outline" size="28" />
        <div>
          <div class="text-subtitle-2">Blocked or redacted trace runs exist, but no persistent incident is stored.</div>
          <div class="text-body-2 mb-3">
            Review the Traces tab for the runtime evidence. Incident aggregation is only created for persistent gate traces.
          </div>
          <v-chip
            v-for="run in blockedRuns.slice(0, 4)"
            :key="run.trace_id"
            size="small"
            class="mr-2 mb-2"
            variant="flat"
          >
            {{ run.trace_id.slice(0, 10) }} · {{ run.tool_calls_blocked }} blocked
          </v-chip>
        </div>
      </div>
    </v-card>

    <v-card v-else variant="tonal" class="text-center py-8">
      <v-icon icon="mdi-shield-check-outline" size="44" class="mb-2" />
      <div class="text-subtitle-2">No incidents recorded yet</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        Run chats that produce blocks or redactions, then review the Traces tab for evidence.
      </div>
      <v-btn size="small" variant="tonal" prepend-icon="mdi-timeline-clock-outline" @click="$emit('openTraces')">
        Open Traces
      </v-btn>
    </v-card>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAgentIncidents } from '~/composables/useAgentControlTraces'
import { useAgentTraceRuns } from '~/composables/useAgentTraceRuns'
import type { IncidentSeverity, IncidentStatus } from '~/types/agentControl'

const props = defineProps<{ agentId: string }>()
defineEmits<{ openTraces: [] }>()

const status = ref<string | undefined>()
const hasBlocks = ref<boolean | null>(true)
const errorText = ref('')

const { incidents, isLoading, refetch, updateIncident } = useAgentIncidents(() => props.agentId, { status })
const { items: blockedRuns, isLoading: tracesLoading, refetch: refetchRuns } = useAgentTraceRuns(() => props.agentId, { hasBlocks })

const statusItems: IncidentStatus[] = ['open', 'acknowledged', 'resolved', 'false_positive']

const headers = [
  { title: 'Title', key: 'title' },
  { title: 'Severity', key: 'severity', width: '110' },
  { title: 'Category', key: 'category', width: '150' },
  { title: 'Status', key: 'status', width: '180' },
  { title: 'Traces', key: 'trace_count', width: '90' },
  { title: 'First Seen', key: 'first_seen', width: '190' },
]

async function updateStatus(incidentId: string, value: string) {
  errorText.value = ''
  try {
    await updateIncident({ incidentId, status: value as IncidentStatus })
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to update incident'
  }
}

function refreshAll() {
  refetch()
  refetchRuns()
}

function severityColor(s: IncidentSeverity) {
  return ({ low: 'green', medium: 'amber', high: 'orange', critical: 'red' })[s] ?? 'grey'
}
</script>
