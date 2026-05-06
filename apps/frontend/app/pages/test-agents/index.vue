<template>
  <v-container fluid class="agent-sandbox pa-0">
    <aside class="agent-sandbox__tree">
      <div class="pa-4 d-flex align-center justify-space-between">
        <div>
          <h1 class="text-subtitle-1 mb-1">Agent Sandbox</h1>
          <p class="text-caption text-medium-emphasis mb-0">OpenClaw shell with runtime gates</p>
        </div>
        <v-btn icon="mdi-refresh" size="small" variant="text" :loading="teamsLoading" @click="refetchTeams" />
      </div>
      <v-divider />

      <div class="pa-3">
        <v-btn block color="primary" variant="tonal" prepend-icon="mdi-shape-plus-outline" @click="navigateTo('/agents/templates')">
          Templates
        </v-btn>
      </div>

      <v-list density="compact" nav class="agent-tree-list">
        <template v-for="team in teams" :key="team.main_agent.id">
          <v-list-item
            :active="config.agentId === team.main_agent.id"
            :title="team.main_agent.name"
            :subtitle="`${team.sub_agents.length} subagents · ${team.tools_count} tools`"
            active-class="agent-tree-active"
            @click="selectAgent(team.main_agent.id)"
          >
            <template #prepend>
              <v-icon icon="mdi-account-supervisor-circle-outline" />
            </template>
          </v-list-item>
          <v-list-item
            v-for="sub in team.sub_agents"
            :key="sub.agent.id"
            class="agent-tree-sub"
            :active="selectedInspectorAgentId === sub.agent.id"
            :title="sub.agent.name"
            :subtitle="sub.binding?.when_to_delegate || 'Subagent'"
            active-class="agent-tree-active"
            @click="inspectAgent(sub.agent.id)"
          >
            <template #prepend>
              <v-icon icon="mdi-subdirectory-arrow-right" size="16" />
            </template>
          </v-list-item>
        </template>
      </v-list>
    </aside>

    <main class="agent-sandbox__chat">
      <agent-chat
        :messages="messages"
        :is-loading="isLoading"
        @send="sendMessage"
        @open-scenarios="showScenarios = true"
      />
    </main>

    <aside class="agent-sandbox__inspector">
      <agent-config
        :agent-id="config.agentId"
        :role="config.role"
        :policy="config.policy"
        :model="config.model"
        :disabled="isLoading"
        @update:agent-id="selectAgent"
        @update:role="switchRole"
        @update:policy="config.policy = $event"
        @update:model="config.model = $event"
        @new-conversation="newConversation"
      />

      <v-card variant="flat" class="agent-inspector">
        <v-card-title class="text-subtitle-1">
          <v-icon start>mdi-sitemap-outline</v-icon>
          Agent Team
        </v-card-title>
        <v-card-text v-if="inspectedAgent">
          <div class="d-flex align-center ga-2 mb-2">
            <v-chip size="x-small" :color="inspectedAgent.agent_kind === 'main_agent' ? 'primary' : 'secondary'" variant="tonal">
              {{ inspectedAgent.agent_kind === 'main_agent' ? 'main agent' : 'subagent' }}
            </v-chip>
            <v-chip size="x-small" variant="tonal">{{ inspectedAgent.rollout_mode }}</v-chip>
          </div>
          <h2 class="text-subtitle-2 mb-1">{{ inspectedAgent.name }}</h2>
          <p class="text-body-2 text-medium-emphasis">{{ inspectedAgent.description || 'No description' }}</p>

          <template v-if="selectedTeam && inspectedAgent.agent_kind === 'main_agent'">
            <v-divider class="my-3" />
            <div class="text-caption text-medium-emphasis mb-2">Subagents</div>
            <v-chip
              v-for="sub in selectedTeam.sub_agents"
              :key="sub.agent.id"
              size="small"
              class="mr-1 mb-1"
              variant="tonal"
              @click="inspectAgent(sub.agent.id)"
            >
              {{ sub.agent.name }}
            </v-chip>
          </template>

          <template v-if="inspectedRuntimeSpec">
            <v-divider class="my-3" />
          <div class="text-caption text-medium-emphasis mb-2">Tools</div>
            <v-chip v-for="tool in inspectedRuntimeSpec.tools" :key="tool.name" size="small" class="mr-1 mb-1" variant="tonal">
              {{ tool.name }}
              <span v-if="tool.provider_type === 'openclaw'" class="ml-1 text-caption">
                · OC · pre {{ tool.pre_gate_enabled === false ? 'off' : 'on' }} · post {{ tool.post_gate_enabled === false ? 'off' : 'on' }}
              </span>
          </v-chip>

            <template v-if="inspectedRuntimeSpec.sub_agents.length">
              <div class="text-caption text-medium-emphasis mt-3 mb-2">Delegation Targets</div>
              <v-chip
                v-for="subAgent in inspectedRuntimeSpec.sub_agents"
                :key="subAgent.agent_id"
                size="small"
                class="mr-1 mb-1"
                variant="outlined"
              >
                {{ subAgent.name }} -> {{ subAgent.openclaw_agent_id || 'unmapped' }}
              </v-chip>
            </template>

            <div class="text-caption text-medium-emphasis mt-3 mb-2">Skills</div>
            <v-chip v-for="skill in inspectedRuntimeSpec.skills" :key="skill.name" size="small" class="mr-1 mb-1" variant="outlined">
              {{ skill.name }}
            </v-chip>
          </template>
        </v-card-text>
      </v-card>

      <agent-trace-panel :trace="lastTrace" :decision="lastFirewallDecision" />
    </aside>

    <attack-scenarios-panel
      v-model="showScenarios"
      :scenarios="scenarios ?? []"
      :loading="scenariosLoading"
      @send="handleAttackSend"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAgentChat } from '~/composables/useAgentChat'
import { useAgentRuntimeSpec } from '~/composables/useAgentRuntimeSpec'
import { useAgentTeams } from '~/composables/useAgentTeams'
import { useModels } from '~/composables/useModels'
import { useRememberedModel } from '~/composables/useRememberedModel'
import { useScenarios } from '~/composables/useScenarios'
import type { AgentRead } from '~/types/wizard'
import type { ScenarioItem } from '~/types/scenarios'

definePageMeta({ title: 'Agent Sandbox' })

const route = useRoute()
const {
  messages,
  isLoading,
  config,
  lastTrace,
  lastFirewallDecision,
  sendMessage,
  switchRole,
  newConversation,
} = useAgentChat()
const { teams, isLoading: teamsLoading, refetch: refetchTeams } = useAgentTeams()
const { scenarios, isLoading: scenariosLoading } = useScenarios('agent')
const { groupedModels, refreshAvailability } = useModels()
const rememberedModel = useRememberedModel('agent')

const showScenarios = ref(false)
const selectedInspectorAgentId = ref<string | null>(null)
const inspectedAgentId = computed(() => selectedInspectorAgentId.value || config.agentId)
const { runtimeSpec: inspectedRuntimeSpec } = useAgentRuntimeSpec(inspectedAgentId)

const selectedTeam = computed(() =>
  teams.value.find(team => team.main_agent.id === config.agentId) ?? null,
)

const inspectedAgent = computed<AgentRead | null>(() => {
  const id = inspectedAgentId.value
  if (!id) return null
  for (const team of teams.value) {
    if (team.main_agent.id === id) return team.main_agent
    const sub = team.sub_agents.find(item => item.agent.id === id)
    if (sub) return sub.agent
  }
  return null
})

watch(
  teams,
  (items) => {
    if (!items.length) return
    const requested = typeof route.query.agent === 'string' ? route.query.agent : ''
    const allMainIds = items.map(team => team.main_agent.id)
    if (requested && allMainIds.includes(requested)) {
      selectAgent(requested)
      return
    }
    if (!config.agentId || !allMainIds.includes(config.agentId)) {
      selectAgent(items[0].main_agent.id)
    }
  },
  { immediate: true },
)

watch(
  groupedModels,
  (models) => {
    const saved = rememberedModel.get()
    if (saved && models.some(m => m.id === saved && m.available)) {
      config.model = saved
      return
    }
    const preferred = models.find(m => m.id === 'deepseek-chat' && m.available) || models.find(m => m.available)
    config.model = preferred?.id ?? ''
  },
  { immediate: true },
)

watch(() => config.model, id => rememberedModel.set(id))

onMounted(() => refreshAvailability())

function selectAgent(id: string | null) {
  config.agentId = id
  selectedInspectorAgentId.value = id
  newConversation()
}

function inspectAgent(id: string) {
  selectedInspectorAgentId.value = id
}

function handleAttackSend(prompt: string, _scenario: ScenarioItem) {
  showScenarios.value = false
  sendMessage(prompt)
}
</script>

<style lang="scss" scoped>
.agent-sandbox {
  height: calc(100vh - 64px);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 340px;
  overflow: hidden;

  &__tree,
  &__inspector {
    overflow-y: auto;
    background: rgb(var(--v-theme-surface));
  }

  &__tree {
    border-right: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  }

  &__chat {
    min-width: 0;
    min-height: 0;
  }

  &__inspector {
    border-left: 1px solid rgba(var(--v-theme-on-surface), 0.12);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
}

.agent-tree-sub {
  padding-left: 28px !important;
}

:deep(.agent-tree-active) {
  background: rgba(var(--v-theme-primary), 0.12) !important;
}

.agent-inspector {
  border-radius: 12px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.12) !important;
}

@media (max-width: 1100px) {
  .agent-sandbox {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;

    &__tree,
    &__inspector {
      border: 0;
      max-height: none;
    }
  }
}
</style>
