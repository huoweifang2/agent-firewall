<template>
  <v-container fluid class="middleware-page pa-4">
    <div class="middleware-page__header">
      <div>
        <h1 class="text-h5 mb-1">
          <v-icon start>mdi-transfer-right</v-icon>
          Skills & Hooks
        </h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Discover local OpenClaw agents, bind skills as protected tools, and audit available hooks.
        </p>
      </div>
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="isAgentsLoading || isToolsLoading || isSkillsLoading || isHooksLoading || isOpenClawAgentsLoading"
        @click="refreshAll"
      />
    </div>

    <v-sheet border rounded class="pa-3 mb-4">
      <div class="middleware-page__agent-row">
        <v-select
          v-model="selectedAgentId"
          :items="agentItems"
          :loading="isAgentsLoading"
          item-title="title"
          item-value="value"
          label="Agent"
          variant="outlined"
          density="compact"
          hide-details
          class="middleware-page__agent-select"
        />
        <v-chip v-if="selectedAgent" size="small" variant="tonal" color="primary">
          {{ selectedAgent.name }}
        </v-chip>
        <v-chip v-if="enabledOpenClawTools.length" size="small" variant="tonal" color="success">
          {{ enabledOpenClawTools.length }} OpenClaw enabled
        </v-chip>
      </div>
    </v-sheet>

    <div class="middleware-page__summary">
      <v-sheet border rounded class="pa-3">
        <div class="text-caption text-medium-emphasis mb-1">OpenClaw runtime</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="openClawStatusOk ? 'success' : 'warning'" icon="mdi-pulse" />
          <span class="text-body-2">{{ openClawStatusOk ? 'Reachable' : 'Status unavailable' }}</span>
        </div>
      </v-sheet>
      <v-sheet border rounded class="pa-3">
        <div class="text-caption text-medium-emphasis mb-1">Local agents</div>
        <div class="text-h6">{{ openClawAgents.length }}</div>
      </v-sheet>
      <v-sheet border rounded class="pa-3">
        <div class="text-caption text-medium-emphasis mb-1">Loadable hooks</div>
        <div class="text-h6">{{ loadableHooks.length }}</div>
      </v-sheet>
    </div>

    <v-alert
      v-if="!selectedAgentId && !isAgentsLoading"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      Create or select a main agent before binding OpenClaw skills.
    </v-alert>

    <v-alert
      v-if="errorText"
      type="error"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="errorText = ''"
    >
      {{ errorText }}
    </v-alert>

    <v-sheet border rounded>
      <v-toolbar density="compact" color="transparent">
        <v-toolbar-title class="text-subtitle-1">OpenClaw Skills</v-toolbar-title>
        <template #append>
          <v-chip size="x-small" variant="outlined" label>
            Runtime config
          </v-chip>
        </template>
      </v-toolbar>
      <v-divider />

      <div v-if="isSkillsLoading || isToolsLoading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-table v-else density="comfortable" class="middleware-table">
        <thead>
          <tr>
            <th class="text-left">Skill</th>
            <th class="text-center">Enabled</th>
            <th class="text-center">Pre-Tool Gate</th>
            <th class="text-center">Post-Tool Gate</th>
            <th class="text-left">Runtime Tool</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!openClawSkills.length">
            <td colspan="5" class="text-center text-medium-emphasis py-8">
              No eligible OpenClaw skills were returned by the backend.
            </td>
          </tr>
          <tr v-for="skill in openClawSkills" :key="skill.name">
            <td>
              <div class="d-flex align-center ga-3">
                <v-avatar color="primary" variant="tonal" rounded="sm" size="32">
                  <span class="text-caption">{{ skill.emoji || 'OC' }}</span>
                </v-avatar>
                <div class="middleware-table__skill">
                  <div class="text-subtitle-2">{{ skill.name }}</div>
                  <div class="text-caption text-medium-emphasis">{{ skill.description || 'OpenClaw skill' }}</div>
                </div>
              </div>
            </td>
            <td class="text-center">
              <v-switch
                :model-value="!!toolForSkill(skill.name)"
                color="success"
                hide-details
                density="compact"
                class="d-inline-flex"
                :disabled="!selectedAgentId || isMutatingSkill(skill.name)"
                :loading="isMutatingSkill(skill.name)"
                @update:model-value="toggleSkill(skill.name, !!$event)"
              />
            </td>
            <td class="text-center">
              <v-switch
                :model-value="preGateEnabled(toolForSkill(skill.name))"
                color="warning"
                hide-details
                density="compact"
                class="d-inline-flex"
                :disabled="!toolForSkill(skill.name) || isUpdating"
                @update:model-value="setProtection(skill.name, 'pre_gate_enabled', !!$event)"
              />
            </td>
            <td class="text-center">
              <v-switch
                :model-value="postGateEnabled(toolForSkill(skill.name))"
                color="warning"
                hide-details
                density="compact"
                class="d-inline-flex"
                :disabled="!toolForSkill(skill.name) || isUpdating"
                @update:model-value="setProtection(skill.name, 'post_gate_enabled', !!$event)"
              />
            </td>
            <td>
              <code v-if="toolForSkill(skill.name)" class="text-caption">{{ toolForSkill(skill.name)?.name }}</code>
              <span v-else class="text-caption text-medium-emphasis">Not bound</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-sheet>

    <div class="middleware-page__grid mt-4">
      <v-sheet border rounded>
        <v-toolbar density="compact" color="transparent">
          <v-toolbar-title class="text-subtitle-1">OpenClaw Agents</v-toolbar-title>
        </v-toolbar>
        <v-divider />
        <v-list density="compact" lines="two">
          <v-list-item v-if="!openClawAgents.length && !isOpenClawAgentsLoading" title="No OpenClaw agents found" />
          <v-list-item
            v-for="agent in openClawAgents"
            :key="agent.id"
            :title="agent.name || agent.id"
            :subtitle="`${agent.id} · ${agentModel(agent.model)}`"
          >
            <template #prepend>
              <v-icon :color="agent.is_default ? 'primary' : undefined" icon="mdi-robot-outline" />
            </template>
            <template #append>
              <v-chip v-if="agent.is_default" size="x-small" color="primary" variant="tonal">default</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </v-sheet>

      <v-sheet border rounded>
        <v-toolbar density="compact" color="transparent">
          <v-toolbar-title class="text-subtitle-1">OpenClaw Hooks</v-toolbar-title>
        </v-toolbar>
        <v-divider />
        <v-table density="compact">
          <thead>
            <tr>
              <th class="text-left">Hook</th>
              <th class="text-left">Events</th>
              <th class="text-center">Loadable</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!openClawHooks.length && !isHooksLoading">
              <td colspan="3" class="text-center text-medium-emphasis py-6">No hooks returned by OpenClaw.</td>
            </tr>
            <tr v-for="hook in openClawHooks" :key="hook.name">
              <td>
                <div class="text-subtitle-2">{{ hook.name }}</div>
                <div class="text-caption text-medium-emphasis">{{ hook.description }}</div>
              </td>
              <td>
                <v-chip v-for="event in hook.events" :key="event" size="x-small" class="mr-1" variant="tonal">
                  {{ event }}
                </v-chip>
              </td>
              <td class="text-center">
                <v-icon :color="hook.loadable ? 'success' : 'warning'" :icon="hook.loadable ? 'mdi-check-circle' : 'mdi-alert-circle-outline'" />
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-sheet>
    </div>

    <v-snackbar v-model="snackbar" :timeout="2600" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAgents } from '~/composables/useAgents'
import { useAgentTools, useOpenClawAgents, useOpenClawHooks, useOpenClawSkills, useOpenClawStatus } from '~/composables/useAgentTools'
import type { ToolRead } from '~/types/wizard'

definePageMeta({ title: 'Skills & Hooks' })

type ProtectionKey = 'pre_gate_enabled' | 'post_gate_enabled'

const mainAgentKind = computed(() => 'main_agent')
const selectedAgentId = ref('')
const pendingSkill = ref('')
const errorText = ref('')
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const { agents, isLoading: isAgentsLoading, refetch: refetchAgents } = useAgents({ agentKind: mainAgentKind })
const {
  tools,
  isLoading: isToolsLoading,
  deleteTool,
  updateTool,
  importOpenClawTools,
  isDeleting,
  isUpdating,
  isImportingOpenClaw,
  refetch: refetchTools,
} = useAgentTools(() => selectedAgentId.value)
const { data: skillsResponse, isLoading: isSkillsLoading, refetch: refetchSkills } = useOpenClawSkills()
const { data: hooksResponse, isLoading: isHooksLoading, refetch: refetchHooks } = useOpenClawHooks()
const { data: openClawAgentsResponse, isLoading: isOpenClawAgentsLoading, refetch: refetchOpenClawAgents } = useOpenClawAgents()
const { data: openClawStatus, refetch: refetchOpenClawStatus } = useOpenClawStatus()

const openClawSkills = computed(() => skillsResponse.value?.items ?? [])
const openClawHooks = computed(() => hooksResponse.value?.items ?? [])
const openClawAgents = computed(() => openClawAgentsResponse.value?.items ?? [])
const openClawStatusOk = computed(() => !!openClawStatus.value?.status)
const loadableHooks = computed(() => openClawHooks.value.filter(hook => hook.loadable && !hook.disabled))
const enabledOpenClawTools = computed(() => tools.value.filter(t => t.category === 'openclaw' || t.name.startsWith('openclaw_')))
const selectedAgent = computed(() => agents.value.find(agent => agent.id === selectedAgentId.value) ?? null)
const agentItems = computed(() =>
  agents.value.map(agent => ({
    title: agent.name,
    value: agent.id,
  })),
)

watch(
  agents,
  (items) => {
    if (selectedAgentId.value && items.some(agent => agent.id === selectedAgentId.value)) return
    selectedAgentId.value = items[0]?.id ?? ''
  },
  { immediate: true },
)

function openClawToolName(skillName: string) {
  const slug = skillName.trim().replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase()
  return `openclaw_${slug || 'skill'}`.slice(0, 64)
}

function toolForSkill(skillName: string): ToolRead | undefined {
  const name = openClawToolName(skillName)
  return tools.value.find(tool => tool.name === name)
}

function providerConfig(tool?: ToolRead): Record<string, unknown> {
  const provider = tool?.arg_schema?.provider
  return provider && typeof provider === 'object' && !Array.isArray(provider)
    ? provider as Record<string, unknown>
    : {}
}

function protectionConfig(tool?: ToolRead): Record<string, unknown> {
  const protection = providerConfig(tool).protection
  return protection && typeof protection === 'object' && !Array.isArray(protection)
    ? protection as Record<string, unknown>
    : {}
}

function gateEnabled(tool: ToolRead | undefined, key: ProtectionKey): boolean {
  const protection = protectionConfig(tool)
  if (typeof protection[key] === 'boolean') return protection[key]

  const provider = providerConfig(tool)
  if (typeof provider[key] === 'boolean') return provider[key] as boolean

  return true
}

function preGateEnabled(tool?: ToolRead) {
  return gateEnabled(tool, 'pre_gate_enabled')
}

function postGateEnabled(tool?: ToolRead) {
  return gateEnabled(tool, 'post_gate_enabled')
}

function withProtection(tool: ToolRead, key: ProtectionKey, enabled: boolean): Record<string, unknown> {
  const currentSchema = tool.arg_schema ? { ...tool.arg_schema } : {}
  const currentProvider = providerConfig(tool)
  const currentProtection = protectionConfig(tool)

  return {
    ...currentSchema,
    provider: {
      ...currentProvider,
      protection: {
        ...currentProtection,
        [key]: enabled,
      },
    },
  }
}

function isMutatingSkill(skillName: string) {
  return pendingSkill.value === skillName || isImportingOpenClaw.value || isDeleting.value
}

function notify(text: string, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

async function toggleSkill(skillName: string, enabled: boolean) {
  if (!selectedAgentId.value) return
  pendingSkill.value = skillName
  errorText.value = ''
  try {
    const existing = toolForSkill(skillName)
    if (enabled && !existing) {
      await importOpenClawTools([skillName])
      notify(`${skillName} enabled`)
    } else if (!enabled && existing) {
      await deleteTool(existing.id)
      notify(`${skillName} disabled`, 'info')
    }
    await refetchTools()
    await refetchAgents()
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : `Failed to update ${skillName}`
  } finally {
    pendingSkill.value = ''
  }
}

async function setProtection(skillName: string, key: ProtectionKey, enabled: boolean) {
  const tool = toolForSkill(skillName)
  if (!tool) return
  errorText.value = ''
  try {
    await updateTool({
      toolId: tool.id,
      body: {
        arg_schema: withProtection(tool, key, enabled),
      },
    })
    notify(`${skillName} ${key === 'pre_gate_enabled' ? 'pre-tool' : 'post-tool'} gate ${enabled ? 'enabled' : 'disabled'}`)
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : `Failed to update ${skillName}`
  }
}

async function refreshAll() {
  await Promise.all([
    refetchAgents(),
    selectedAgentId.value ? refetchTools() : Promise.resolve(),
    refetchSkills(),
    refetchHooks(),
    refetchOpenClawAgents(),
    refetchOpenClawStatus(),
  ])
}

function agentModel(model: string | Record<string, unknown> | null) {
  if (!model) return 'model unknown'
  if (typeof model === 'string') return model
  const primary = model.primary
  return typeof primary === 'string' ? primary : 'model configured'
}
</script>

<style scoped>
.middleware-page {
  max-width: 1180px;
  margin: 0 auto;
}

.middleware-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.middleware-page__agent-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.middleware-page__agent-select {
  max-width: 360px;
  min-width: 260px;
}

.middleware-page__summary,
.middleware-page__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.middleware-page__grid {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
}

.middleware-table__skill {
  max-width: 520px;
}

.middleware-table :deep(th) {
  white-space: nowrap;
}

.middleware-table :deep(td) {
  vertical-align: middle;
}

@media (max-width: 720px) {
  .middleware-page__header {
    align-items: flex-start;
  }

  .middleware-page__agent-select {
    max-width: none;
    min-width: 100%;
  }

  .middleware-page__summary,
  .middleware-page__grid {
    grid-template-columns: 1fr;
  }
}
</style>
