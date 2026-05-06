<template>
  <v-card variant="flat" class="agent-config">
    <v-card-title class="text-subtitle-1">
      <v-icon class="main-icon" start>mdi-cog</v-icon>
      OpenClaw Shell
    </v-card-title>

    <v-card-text>
      <v-select
        :model-value="agentId"
        :items="agentItems"
        :loading="isAgentsLoading"
        :disabled="disabled"
        label="Agent"
        variant="outlined"
        density="compact"
        hide-details
        item-title="name"
        item-value="id"
        class="mb-4"
        @update:model-value="$emit('update:agentId', $event)"
      />

      <v-select
        :model-value="role"
        :items="roleItems"
        :loading="isRuntimeLoading"
        :disabled="disabled || !agentId"
        label="User Role"
        variant="outlined"
        density="compact"
        hide-details
        class="mb-4"
        @update:model-value="$emit('update:role', $event)"
      />

      <v-alert
        v-if="agentId && runtimeSpec"
        variant="tonal"
        color="info"
        density="compact"
        class="mb-4"
      >
        OpenClaw {{ runtimeSpec.openclaw_agent_id || 'coder' }} · {{ skills.length }} skills · {{ subAgents.length }} sub-agents · {{ runtimeSpec.tools.length }} tools
      </v-alert>

      <v-select
        :model-value="model"
        :items="modelItems"
        :loading="isModelsLoading"
        :disabled="disabled"
        label="Model"
        variant="outlined"
        density="compact"
        hide-details
        item-title="title"
        item-value="value"
        class="mb-4"
        @update:model-value="$emit('update:model', $event)"
      />

      <v-select
        :model-value="policy"
        :items="policyItems"
        :loading="isPoliciesLoading"
        :disabled="disabled"
        label="Policy"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="mb-4"
        @update:model-value="$emit('update:policy', $event)"
      />

      <v-btn
        block
        variant="outlined"
        color="secondary"
        :disabled="disabled"
        prepend-icon="mdi-refresh"
        @click="$emit('new-conversation')"
      >
        New Conversation
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, toRef, watch } from 'vue'
import { usePolicies } from '~/composables/usePolicies'
import { useModels } from '~/composables/useModels'
import { useAgents } from '~/composables/useAgents'
import { useAgentRuntimeSpec } from '~/composables/useAgentRuntimeSpec'
import { sortedPolicyItems } from '~/utils/policyOrder'

const props = defineProps<{
  agentId?: string | null
  role: string
  policy: string | null
  model: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:agentId': [value: string | null]
  'update:role': [value: string]
  'update:policy': [value: string | null]
  'update:model': [value: string]
  'new-conversation': []
}>()

const mainAgentKind = computed(() => 'main_agent')
const { agents, isLoading: isAgentsLoading } = useAgents({ agentKind: mainAgentKind })
const { policies, isLoading: isPoliciesLoading } = usePolicies()
const { groupedModels, isLoading: isModelsLoading } = useModels()
const { runtimeSpec, roles, skills, subAgents, isLoading: isRuntimeLoading } = useAgentRuntimeSpec(toRef(props, 'agentId'))

const roleItems = computed(() => {
  if (roles.value.length > 0) {
    return roles.value.map((role) => ({
      title: role.name,
      value: role.name,
    }))
  }

  if (props.role) {
    return [{ title: props.role, value: props.role }]
  }

  return []
})

const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  mock: 'Demo',
}

const agentItems = computed(() => agents.value ?? [])

/** Only show models enabled by the local runtime. */
const modelItems = computed(() =>
  (groupedModels.value ?? [])
    .filter((m) => m.available)
    .map((m) => ({
      title: `${m.name}  ·  ${PROVIDER_LABELS[m.provider] ?? m.provider}`,
      value: m.id,
    })),
)

const policyItems = computed(() => sortedPolicyItems(policies.value ?? []))

watch(
  [() => props.agentId, roleItems, runtimeSpec],
  () => {
    if (!props.agentId) return
    const validRoles = roleItems.value.map((item) => item.value)
    if (validRoles.includes(props.role)) return
    const fallbackRole = runtimeSpec.value?.default_role ?? validRoles[0]
    if (fallbackRole) {
      emit('update:role', fallbackRole)
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped>
.agent-config {
  padding: 8px 0;
  border-radius: 12px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.12) !important;
  background: rgb(var(--v-theme-surface));

  .main-icon {
    font-size: 24px;
  }
}
</style>
