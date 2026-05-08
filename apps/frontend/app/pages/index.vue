<template>
  <v-container fluid class="dashboard-page">
    <div class="dashboard-header mb-6">
      <div>
        <h1 class="text-h5 mb-1">Agent-Firewall Console</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Runtime status, active evidence, and the fastest paths into local testing.
        </p>
      </div>
      <div class="d-flex align-center ga-2">
        <v-btn variant="tonal" prepend-icon="mdi-shield-search" to="/red-team">
          Attack Playground
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-chat-processing-outline" to="/playground">
          Playground
        </v-btn>
      </div>
    </div>

    <v-row class="mb-4">
      <v-col v-for="service in serviceCards" :key="service.title" cols="12" sm="6" lg="3">
        <v-card variant="outlined" class="status-card">
          <v-card-text>
            <div class="d-flex align-center justify-space-between mb-3">
              <div class="d-flex align-center ga-2">
                <v-avatar :color="service.color" variant="tonal" rounded="sm" size="36">
                  <v-icon :icon="service.icon" />
                </v-avatar>
                <div>
                  <div class="text-subtitle-2 font-weight-bold">{{ service.title }}</div>
                  <div class="text-caption text-medium-emphasis">{{ service.detail }}</div>
                </div>
              </div>
              <v-chip :color="service.color" size="x-small" variant="tonal">
                {{ service.status }}
              </v-chip>
            </div>
            <div class="text-caption text-medium-emphasis">{{ service.hint }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="metric-card">
          <v-card-title class="text-subtitle-1">Traffic</v-card-title>
          <v-card-text>
            <div class="metric-value">{{ summary?.total_requests ?? 0 }}</div>
            <div class="text-body-2 text-medium-emphasis">
              {{ summary?.blocked ?? 0 }} blocked · {{ summary?.modified ?? 0 }} modified · {{ summary?.allowed ?? 0 }} allowed
            </div>
            <v-btn class="mt-4" variant="tonal" size="small" prepend-icon="mdi-format-list-bulleted-square" to="/requests">
              Open Requests
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card variant="outlined" class="metric-card">
          <v-card-title class="text-subtitle-1">Bot Agent Teams</v-card-title>
          <v-card-text>
            <div class="metric-value">{{ teams.length }}</div>
            <div class="text-body-2 text-medium-emphasis">
              {{ subAgentCount }} subagents · {{ toolCount }} tools · {{ roleCount }} roles
            </div>
            <v-btn class="mt-4" variant="tonal" size="small" prepend-icon="mdi-robot-outline" to="/agents">
              Manage Agents
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card variant="outlined" class="metric-card">
          <v-card-title class="text-subtitle-1">Risk</v-card-title>
          <v-card-text>
            <div class="metric-value">{{ formatPct(summary?.block_rate ?? 0) }}</div>
            <div class="text-body-2 text-medium-emphasis">
              Avg risk {{ (summary?.avg_risk ?? 0).toFixed(2) }} · {{ summary?.top_intent || 'no dominant intent' }}
            </div>
            <v-btn class="mt-4" variant="tonal" size="small" prepend-icon="mdi-chart-box-outline" to="/analytics">
              Open Analytics
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" lg="7">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center justify-space-between">
            <span class="text-subtitle-1">Operational Shortcuts</span>
            <v-btn variant="text" size="small" icon="mdi-refresh" :loading="summaryLoading || teamsLoading" @click="refreshDashboard" />
          </v-card-title>
          <v-divider />
          <v-list density="compact" lines="two">
            <v-list-item
              v-for="shortcut in shortcuts"
              :key="shortcut.to"
              :to="shortcut.to"
              :title="shortcut.title"
              :subtitle="shortcut.subtitle"
            >
              <template #prepend>
                <v-icon :icon="shortcut.icon" />
              </template>
              <template #append>
                <v-icon icon="mdi-chevron-right" />
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="12" lg="5">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">Runtime Notes</v-card-title>
          <v-divider />
          <v-card-text>
            <v-alert v-if="agentError" type="warning" variant="tonal" density="compact" class="mb-3">
              Agent Runtime is not reachable at the configured local endpoint.
            </v-alert>
            <v-alert v-else-if="openClawError" type="warning" variant="tonal" density="compact" class="mb-3">
              {{ openClawError }}
            </v-alert>
            <div class="runtime-list">
              <div class="runtime-row">
                <span class="text-medium-emphasis">Default model</span>
                <strong>{{ openClawConfig?.default_model || 'unknown' }}</strong>
              </div>
              <div class="runtime-row">
                <span class="text-medium-emphasis">Gateway mode</span>
                <strong>{{ openClawConfig?.gateway_mode || 'unknown' }}</strong>
              </div>
              <div class="runtime-row">
                <span class="text-medium-emphasis">Telegram accounts</span>
                <strong>{{ openClawConfig?.telegram_bridge_accounts ?? openClawConfig?.telegram_accounts ?? 0 }}</strong>
              </div>
              <div class="runtime-row">
                <span class="text-medium-emphasis">Last proxy check</span>
                <strong>{{ lastChecked ? lastChecked.toLocaleTimeString() : 'pending' }}</strong>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { agentService } from '~/services/agentService'
import { useAgentTeams } from '~/composables/useAgentTeams'
import { useAnalytics } from '~/composables/useAnalytics'
import { useHealth } from '~/composables/useHealth'

definePageMeta({ title: 'Dashboard' })

const { status, services, lastChecked } = useHealth()
const { teams, isLoading: teamsLoading, refetch: refetchTeams } = useAgentTeams()
const { summary, summaryLoading, refreshAll } = useAnalytics()

const {
  data: openClawConfig,
  error: agentRuntimeError,
  isLoading: agentLoading,
  refetch: refetchAgent,
} = useQuery({
  queryKey: ['dashboard-agent-runtime'],
  queryFn: agentService.getOpenClawConfig,
  refetchInterval: 30_000,
})

const agentError = computed(() => !!agentRuntimeError.value)
const openClawError = computed(() => openClawConfig.value?.error || '')

const subAgentCount = computed(() => teams.value.reduce((sum, team) => sum + team.sub_agents.length, 0))
const toolCount = computed(() => teams.value.reduce((sum, team) => {
  const subTools = team.sub_agents.reduce((n, sub) => n + sub.tools_count, 0)
  return sum + team.tools_count + subTools
}, 0))
const roleCount = computed(() => teams.value.reduce((sum, team) => {
  const subRoles = team.sub_agents.reduce((n, sub) => n + sub.roles_count, 0)
  return sum + team.roles_count + subRoles
}, 0))

const proxyStatus = computed(() => status.value === 'ok' ? 'ok' : status.value)
const agentStatus = computed(() => {
  if (agentLoading.value) return 'loading'
  if (agentError.value) return 'error'
  return 'ok'
})
const openClawStatus = computed(() => {
  if (agentLoading.value) return 'loading'
  if (!openClawConfig.value) return 'unknown'
  return openClawConfig.value.status_ok && openClawConfig.value.models_ok && openClawConfig.value.agents_ok ? 'ok' : 'degraded'
})
const telegramStatus = computed(() => {
  if (agentLoading.value) return 'loading'
  if (!openClawConfig.value?.telegram_bridge_enabled) return 'disabled'
  return openClawConfig.value.telegram_bridge_running ? 'running' : 'stopped'
})

function cardColor(value: string) {
  if (['ok', 'running'].includes(value)) return 'success'
  if (['loading', 'degraded', 'stopped'].includes(value)) return 'warning'
  if (value === 'disabled') return 'grey'
  return 'error'
}

const serviceCards = computed(() => [
  {
    title: 'Proxy',
    icon: 'mdi-server-security',
    status: proxyStatus.value,
    color: cardColor(proxyStatus.value),
    detail: services.value.db?.status ? `DB ${services.value.db.status}` : 'health pending',
    hint: services.value.redis?.detail ? `Cache: ${services.value.redis.detail}` : `Cache: ${services.value.redis?.status ?? 'unknown'}`,
  },
  {
    title: 'Agent Runtime',
    icon: 'mdi-robot-happy-outline',
    status: agentStatus.value,
    color: cardColor(agentStatus.value),
    detail: openClawConfig.value?.openclaw_agent_id || 'localhost:8002',
    hint: openClawConfig.value?.deepseek_configured ? 'DeepSeek configured server-side' : 'No server-side DeepSeek key reported',
  },
  {
    title: 'OpenClaw',
    icon: 'mdi-flask-outline',
    status: openClawStatus.value,
    color: cardColor(openClawStatus.value),
    detail: openClawConfig.value?.openclaw_bin || 'openclaw',
    hint: openClawConfig.value?.openclaw_agent_local ? 'Local OpenClaw agent mode' : 'Remote OpenClaw mode',
  },
  {
    title: 'Telegram Bridge',
    icon: 'mdi-send-lock-outline',
    status: telegramStatus.value,
    color: cardColor(telegramStatus.value),
    detail: `${openClawConfig.value?.telegram_bridge_accounts ?? 0} account(s)`,
    hint: openClawConfig.value?.telegram_bridge_last_error || 'No bridge error reported',
  },
])

const shortcuts = [
  {
    title: 'Review pending approvals',
    subtitle: 'Approve, reject, or audit Telegram interventions and tool confirmations.',
    icon: 'mdi-shield-check-outline',
    to: '/approvals',
  },
  {
    title: 'Inspect structured agent traces',
    subtitle: 'Open trace runs with pre-tool gates, post-tool gates, tool execution, and final response.',
    icon: 'mdi-timeline-clock-outline',
    to: '/agent-traces',
  },
  {
    title: 'Manage policies and rules',
    subtitle: 'Edit custom policies, import denylist rules, export rules, and test matches.',
    icon: 'mdi-shield-cog-outline',
    to: '/policies',
  },
  {
    title: 'Compare protected versus direct OpenClaw',
    subtitle: 'Run the same prompt through Agent-Firewall and the local direct runtime.',
    icon: 'mdi-compare-horizontal',
    to: '/compare',
  },
]

function refreshDashboard() {
  refreshAll()
  refetchTeams()
  refetchAgent()
}

function formatPct(value: number) {
  return `${(value * 100).toFixed(0)}%`
}
</script>

<style scoped>
.dashboard-page {
  max-width: 1440px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.status-card,
.metric-card {
  height: 100%;
}

.metric-value {
  font-size: 36px;
  line-height: 1.1;
  font-weight: 700;
  font-feature-settings: 'tnum';
}

.runtime-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.runtime-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

@media (max-width: 760px) {
  .dashboard-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
