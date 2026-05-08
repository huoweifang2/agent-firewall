<template>
  <v-container fluid class="agent-detail-page">
    <!-- Header -->
    <div v-if="agent" class="d-flex align-center justify-space-between mb-4">
      <div class="d-flex align-center">
        <v-btn icon="mdi-arrow-left" variant="text" @click="navigateTo('/agents')" />
        <div class="ml-2">
          <h1 class="text-h5">{{ agent.name }}</h1>
          <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0" />
        </div>
      </div>
      <div class="d-flex ga-2 align-center">
        <v-chip :color="riskColor(agent.risk_level)" variant="tonal" size="small">
          {{ agent.risk_level ?? 'TBD' }}
        </v-chip>
        <v-chip :color="rolloutColor(agent.rollout_mode)" variant="tonal" size="small">
          {{ agent.rollout_mode }}
        </v-chip>
        <v-btn size="small" variant="text" icon="mdi-pencil" @click="navigateTo(`/agents/${agent.id}/edit`)" />
        <v-btn size="small" variant="text" icon="mdi-delete" color="red" @click="showDeleteDialog = true" />
      </div>
    </div>

    <!-- Delete confirmation dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="440">
      <v-card>
        <v-card-title class="text-h6">Delete Agent</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ agent?.name }}</strong>?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="red" variant="flat" :loading="isDeleting" @click="doDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate size="48" />
    </div>

    <template v-else-if="agent">
      <v-tabs v-model="activeTab" density="compact" class="mb-4">
        <v-tab value="overview">Overview</v-tab>
        <v-tab value="team">Agent Team</v-tab>
        <v-tab value="tools">Tools</v-tab>
        <v-tab value="roles">Roles</v-tab>
        <v-tab value="config">Config</v-tab>
        <v-tab value="kit">Integration Kit</v-tab>
        <v-tab value="validation">Validation</v-tab>
        <v-tab value="traces">Traces</v-tab>
        <v-tab value="incidents">Incidents</v-tab>
      </v-tabs>

      <v-tabs-window v-model="activeTab">
        <!-- Overview -->
        <v-tabs-window-item value="overview">
          <v-row>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-4">
                <h3 class="text-subtitle-1 mb-3">Agent Details</h3>
                <v-list density="compact">
                  <v-list-item>
                    <template #title>Description</template>
                    <template #subtitle>{{ agent.description || '—' }}</template>
                  </v-list-item>
                  <v-list-item>
                    <template #title>Framework</template>
                    <template #subtitle>{{ agent.framework }}</template>
                  </v-list-item>
                  <v-list-item>
                    <template #title>Environment</template>
                    <template #subtitle>{{ agent.environment }}</template>
                  </v-list-item>
                  <v-list-item>
                    <template #title>Team</template>
                    <template #subtitle>{{ agent.team || '—' }}</template>
                  </v-list-item>
                  <v-list-item>
                    <template #title>Status</template>
                    <template #subtitle>{{ agent.status }}</template>
                  </v-list-item>
                  <v-list-item>
                    <template #title>Created</template>
                    <template #subtitle>{{ new Date(agent.created_at).toLocaleString() }}</template>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-4">
                <h3 class="text-subtitle-1 mb-3">Rollout</h3>
                <div class="d-flex align-center ga-2 mb-4">
                  <span class="text-body-2">Current mode:</span>
                  <v-chip :color="rolloutColor(agent.rollout_mode)" variant="tonal">
                    {{ agent.rollout_mode }}
                  </v-chip>
                </div>

                <template v-if="readiness">
                  <div v-if="readiness.blockers.length" class="mb-3">
                    <p class="text-caption text-medium-emphasis mb-1">Blockers:</p>
                    <v-alert
                      v-for="(b, i) in readiness.blockers"
                      :key="i"
                      type="warning"
                      variant="tonal"
                      density="compact"
                      class="mb-1"
                    >
                      {{ b }}
                    </v-alert>
                  </div>

                  <div class="d-flex ga-2">
                    <v-btn
                      v-for="target in readiness.can_promote_to"
                      :key="target"
                      size="small"
                      :color="rolloutColor(target)"
                      variant="tonal"
                      :loading="isPromoting"
                      @click="doPromote(target)"
                    >
                      Promote to {{ target }}
                    </v-btn>
                    <v-btn
                      v-if="agent.rollout_mode !== 'observe'"
                      size="small"
                      variant="text"
                      @click="doPromote(agent.rollout_mode === 'enforce' ? 'warn' : 'observe')"
                    >
                      Demote
                    </v-btn>
                  </div>
                </template>

                <div class="mt-4">
                  <h4 class="text-subtitle-2 mb-2">Risk Factors</h4>
                  <v-chip v-if="agent.is_public_facing" size="x-small" class="mr-1 mb-1" color="orange">Public</v-chip>
                  <v-chip v-if="agent.has_write_actions" size="x-small" class="mr-1 mb-1" color="amber">Write actions</v-chip>
                  <v-chip v-if="agent.touches_pii" size="x-small" class="mr-1 mb-1" color="red">PII</v-chip>
                  <v-chip v-if="agent.handles_secrets" size="x-small" class="mr-1 mb-1" color="red">Secrets</v-chip>
                  <v-chip v-if="agent.calls_external_apis" size="x-small" class="mr-1 mb-1" color="amber">External APIs</v-chip>
                </div>
              </v-card>
            </v-col>
            <v-col cols="12">
              <v-card variant="outlined" class="pa-4">
                <div class="d-flex align-center justify-space-between mb-3">
                  <div>
                    <h3 class="text-subtitle-1">Recent Runtime Trace Summary</h3>
                    <p class="text-body-2 text-medium-emphasis mb-0">
                      Last structured runs from this agent's real `/traces/runs` data plane.
                    </p>
                  </div>
                  <v-btn size="small" variant="tonal" prepend-icon="mdi-timeline-clock-outline" @click="activeTab = 'traces'">
                    Open Traces
                  </v-btn>
                </div>
                <v-table v-if="recentTraceRuns.length" density="compact">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Session</th>
                      <th>Intent</th>
                      <th>Tools</th>
                      <th>Decision</th>
                      <th>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="run in recentTraceRuns.slice(0, 5)" :key="run.trace_id">
                      <td>{{ new Date(run.timestamp).toLocaleString() }}</td>
                      <td><code class="text-caption">{{ shortId(run.session_id) }}</code></td>
                      <td>{{ run.intent || 'unknown' }}</td>
                      <td>{{ run.tool_calls_count }} calls · {{ run.tool_calls_blocked }} blocked</td>
                      <td>
                        <v-chip :color="run.firewall_blocked || run.tool_calls_blocked ? 'error' : 'success'" size="x-small" variant="tonal">
                          {{ run.firewall_blocked || run.tool_calls_blocked ? 'blocked evidence' : 'allowed' }}
                        </v-chip>
                      </td>
                      <td>{{ run.total_duration_ms }}ms</td>
                    </tr>
                  </tbody>
                </v-table>
                <v-alert v-else type="info" variant="tonal" density="compact">
                  No structured trace runs yet. Use Playground, Compare, Telegram, or `/agent/chat` to generate one.
                </v-alert>
              </v-card>
            </v-col>
          </v-row>
        </v-tabs-window-item>

        <!-- Agent Team -->
        <v-tabs-window-item value="team">
          <agent-detail-team-tab :agent="agent" :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Tools -->
        <v-tabs-window-item value="tools">
          <agent-detail-tools-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Roles -->
        <v-tabs-window-item value="roles">
          <agent-detail-roles-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Config -->
        <v-tabs-window-item value="config">
          <agent-detail-config-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Integration Kit -->
        <v-tabs-window-item value="kit">
          <agent-detail-kit-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Validation -->
        <v-tabs-window-item value="validation">
          <agent-detail-validation-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Traces -->
        <v-tabs-window-item value="traces">
          <agent-detail-traces-tab :agent-id="agentId" />
        </v-tabs-window-item>

        <!-- Incidents -->
        <v-tabs-window-item value="incidents">
          <agent-detail-incidents-tab :agent-id="agentId" @open-traces="activeTab = 'traces'" />
        </v-tabs-window-item>
      </v-tabs-window>
    </template>

    <v-alert v-else-if="error" type="error" variant="tonal">
      Failed to load agent
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAgents } from '~/composables/useAgents'
import { useAgentRollout } from '~/composables/useAgentRollout'
import { useAgentTraceRuns } from '~/composables/useAgentTraceRuns'
import type { AgentRead, RolloutMode } from '~/types/agentControl'

definePageMeta({ title: 'Agent Detail' })

const route = useRoute()
const agentId = computed(() => route.params.id as string)

const loading = ref(true)
const agent = ref<AgentRead | null>(null)
const error = ref(false)
const activeTab = ref('overview')
const showDeleteDialog = ref(false)

const { getAgent, deleteAgent, isDeleting } = useAgents()
const { readiness, promote, isPromoting } = useAgentRollout(() => agentId.value)
const { items: recentTraceRuns } = useAgentTraceRuns(() => agentId.value)

const breadcrumbs = computed(() => [
  { title: 'Agents', to: '/agents' },
  { title: agent.value?.name ?? 'Agent' },
])

// Colors
const riskColor = (level: string | null) =>
  ({ low: 'green', medium: 'amber', high: 'orange', critical: 'red' })[level ?? ''] ?? 'grey'

const rolloutColor = (mode: RolloutMode) =>
  ({ observe: 'blue', warn: 'amber', enforce: 'green' })[mode] ?? 'grey'

const doPromote = async (mode: RolloutMode) => {
  try {
    await promote(mode)
    // Reload agent to get updated rollout_mode
    agent.value = await getAgent(agentId.value)
  }
  catch { /* */ }
}

const doDelete = async () => {
  if (!agent.value) return
  try {
    await deleteAgent(agent.value.id)
    showDeleteDialog.value = false
    navigateTo('/agents')
  }
  catch { /* */ }
}

const shortId = (value: string) => {
  return value.length > 16 ? `${value.slice(0, 12)}…` : value
}

// Load agent
onMounted(async () => {
  try {
    agent.value = await getAgent(agentId.value)
  }
  catch {
    error.value = true
  }
  finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.config-preview {
  max-height: 400px;
  overflow: auto;
  background: rgba(0, 0, 0, 0.2);

  pre {
    white-space: pre-wrap;
    word-break: break-word;
    font-family: 'Fira Code', monospace;
  }
}
</style>
