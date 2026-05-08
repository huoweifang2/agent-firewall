<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex align-center justify-space-between mb-3">
      <div>
        <h3 class="text-subtitle-1">Trace Runs</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Structured runtime traces from `/v1/agents/{id}/traces/runs`.
        </p>
      </div>
      <v-btn size="small" variant="text" icon="mdi-refresh" :loading="isLoading" @click="refetch" />
    </div>

    <div class="d-flex flex-wrap ga-3 mb-3">
      <v-text-field v-model="sessionId" label="Session ID" density="compact" variant="outlined" clearable hide-details style="max-width: 220px" />
      <v-select v-model="hasBlocks" :items="blockItems" label="Blocks" density="compact" variant="outlined" clearable hide-details item-title="title" item-value="value" style="max-width: 180px" />
      <v-text-field v-model="dateFrom" label="From" type="date" density="compact" variant="outlined" clearable hide-details style="max-width: 160px" />
      <v-text-field v-model="dateTo" label="To" type="date" density="compact" variant="outlined" clearable hide-details style="max-width: 160px" />
      <v-spacer />
      <v-chip v-if="total" size="small" variant="tonal">{{ total }} runs</v-chip>
    </div>

    <agent-traces-table
      v-if="items.length || isLoading"
      v-model:page="page"
      v-model:page-size="pageSize"
      :items="items"
      :total="total"
      :loading="isLoading"
      :fetch-detail="fetchDetail"
      :fetch-export="fetchExport"
    />

    <v-card v-else variant="tonal" class="text-center py-8">
      <v-icon icon="mdi-chart-timeline-variant" size="44" class="mb-2" />
      <div class="text-subtitle-2">No trace runs recorded yet</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        Send a message through Playground, Compare, Telegram, or `/agent/chat` with this agent selected.
      </div>
      <div class="d-flex justify-center ga-2">
        <v-btn size="small" color="primary" prepend-icon="mdi-chat-processing-outline" to="/playground">Open Playground</v-btn>
        <v-btn size="small" variant="tonal" prepend-icon="mdi-compare-horizontal" to="/compare">Open Compare</v-btn>
      </div>
    </v-card>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAgentTraceRuns } from '~/composables/useAgentTraceRuns'

const props = defineProps<{ agentId: string }>()

const sessionId = ref<string | null>(null)
const hasBlocks = ref<boolean | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(25)

const blockItems = [
  { title: 'Has blocks', value: true },
  { title: 'No blocks', value: false },
]

const { items, total, isLoading, refetch, fetchDetail, fetchExport } = useAgentTraceRuns(
  () => props.agentId,
  { sessionId, hasBlocks, dateFrom, dateTo, page, pageSize },
)
</script>

