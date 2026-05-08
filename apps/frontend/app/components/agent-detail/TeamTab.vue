<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex align-center justify-space-between mb-3">
      <div>
        <h3 class="text-subtitle-1">Agent Team</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Bind, edit, enable, or remove subagents used by this main agent.
        </p>
      </div>
      <v-chip v-if="agent.agent_kind" variant="tonal" size="small">
        {{ agent.agent_kind }}
      </v-chip>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <template v-if="agent.agent_kind === 'main_agent'">
      <div class="d-flex flex-wrap ga-2 mb-3">
        <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreate">
          Create Subagent
        </v-btn>
        <v-btn size="small" variant="tonal" prepend-icon="mdi-link-variant-plus" :disabled="!availableAgents.length" @click="openBind">
          Bind Existing
        </v-btn>
        <v-btn size="small" variant="text" icon="mdi-refresh" :loading="loading" @click="refetch" />
      </div>

      <v-list v-if="delegations.length" lines="three" border rounded>
        <v-list-item
          v-for="binding in delegations"
          :key="binding.id"
          :title="binding.child_agent_name || binding.child_agent_id"
          :subtitle="binding.when_to_delegate || binding.delegation_description || 'No delegation rule'"
        >
          <template #prepend>
            <v-icon icon="mdi-call-split" />
          </template>
          <template #append>
            <div class="d-flex align-center ga-1">
              <v-switch
                :model-value="binding.is_active"
                color="success"
                density="compact"
                hide-details
                :loading="isUpdating"
                @update:model-value="(v: boolean | null) => setActive(binding.id, !!v)"
              />
              <v-btn size="small" variant="text" icon="mdi-pencil" @click="openEdit(binding)" />
              <v-btn size="small" variant="text" icon="mdi-arrow-right" @click="navigateTo(`/agents/${binding.child_agent_id}`)" />
              <v-btn size="small" variant="text" icon="mdi-delete" color="error" :loading="isDeleting" @click="removeBinding(binding.id)" />
            </div>
          </template>
        </v-list-item>
      </v-list>

      <v-card v-else variant="tonal" class="text-center py-8">
        <v-icon icon="mdi-account-supervisor-circle-outline" size="44" class="mb-2" />
        <div class="text-subtitle-2">No subagents are bound yet</div>
        <div class="text-body-2 text-medium-emphasis mb-4">Create a specialized worker or bind another existing subagent.</div>
        <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreate">
          Create Subagent
        </v-btn>
      </v-card>
    </template>

    <v-alert v-else type="info" variant="tonal">
      This is a subagent. Its tools, roles, skills, validation, and traces are managed directly on this page.
    </v-alert>

    <v-dialog v-model="dialog" max-width="620">
      <v-card>
        <v-card-title>{{ dialogMode === 'create' ? 'Create Subagent' : dialogMode === 'bind' ? 'Bind Existing Subagent' : 'Edit Delegation' }}</v-card-title>
        <v-card-text>
          <template v-if="dialogMode === 'bind'">
            <v-select
              v-model="bindForm.child_agent_id"
              :items="availableAgents"
              item-title="name"
              item-value="id"
              label="Subagent"
              variant="outlined"
            />
          </template>
          <template v-else-if="dialogMode === 'create'">
            <v-text-field v-model="createForm.name" label="Name" variant="outlined" />
            <v-textarea v-model="createForm.description" label="Responsibility" variant="outlined" rows="2" />
          </template>

          <v-textarea v-model="delegationForm.delegation_description" label="Delegation description" variant="outlined" rows="2" />
          <v-textarea v-model="delegationForm.when_to_delegate" label="When to delegate" variant="outlined" rows="3" />
          <v-switch v-model="delegationForm.is_active" label="Active" color="success" hide-details />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" :disabled="!canSave" @click="save">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useAgents } from '~/composables/useAgents'
import { useAgentDelegations } from '~/composables/useAgentDelegations'
import { useAgentTeams } from '~/composables/useAgentTeams'
import type { AgentRead, DelegationRead } from '~/types/agentControl'

const props = defineProps<{
  agent: AgentRead
  agentId: string
}>()

const { agents } = useAgents()
const { createSubAgent, isCreatingSubAgent } = useAgentTeams()
const {
  delegations,
  isLoading: loading,
  refetch,
  createDelegation,
  updateDelegation,
  deleteDelegation,
  isCreating,
  isUpdating,
  isDeleting,
} = useAgentDelegations(() => props.agentId)

const dialog = ref(false)
const dialogMode = ref<'create' | 'bind' | 'edit'>('create')
const editing = ref<DelegationRead | null>(null)
const errorText = ref('')

const createForm = reactive({
  name: '',
  description: '',
})

const bindForm = reactive({
  child_agent_id: '',
})

const delegationForm = reactive({
  delegation_description: '',
  when_to_delegate: '',
  is_active: true,
})

const availableAgents = computed(() => {
  const bound = new Set(delegations.value.map(d => d.child_agent_id))
  return agents.value.filter(candidate =>
    candidate.id !== props.agentId
    && candidate.agent_kind === 'sub_agent'
    && !bound.has(candidate.id),
  )
})

const saving = computed(() => isCreating.value || isUpdating.value || isCreatingSubAgent.value)
const canSave = computed(() => {
  if (dialogMode.value === 'create') return createForm.name.trim().length >= 2
  if (dialogMode.value === 'bind') return !!bindForm.child_agent_id
  return !!editing.value
})

function resetDelegationForm() {
  delegationForm.delegation_description = ''
  delegationForm.when_to_delegate = ''
  delegationForm.is_active = true
}

function openCreate() {
  dialogMode.value = 'create'
  editing.value = null
  createForm.name = ''
  createForm.description = ''
  resetDelegationForm()
  dialog.value = true
}

function openBind() {
  dialogMode.value = 'bind'
  editing.value = null
  bindForm.child_agent_id = availableAgents.value[0]?.id ?? ''
  resetDelegationForm()
  dialog.value = true
}

function openEdit(binding: DelegationRead) {
  dialogMode.value = 'edit'
  editing.value = binding
  delegationForm.delegation_description = binding.delegation_description
  delegationForm.when_to_delegate = binding.when_to_delegate
  delegationForm.is_active = binding.is_active
  dialog.value = true
}

async function save() {
  errorText.value = ''
  try {
    if (dialogMode.value === 'create') {
      await createSubAgent({
        mainAgentId: props.agentId,
        body: {
          name: createForm.name.trim(),
          description: createForm.description.trim(),
          delegation_description: delegationForm.delegation_description,
          when_to_delegate: delegationForm.when_to_delegate,
          is_active: delegationForm.is_active,
          template_key: 'manual_subagent',
        },
      })
      await refetch()
    } else if (dialogMode.value === 'bind') {
      await createDelegation({
        child_agent_id: bindForm.child_agent_id,
        delegation_description: delegationForm.delegation_description,
        when_to_delegate: delegationForm.when_to_delegate,
        is_active: delegationForm.is_active,
      })
    } else if (editing.value) {
      await updateDelegation({
        bindingId: editing.value.id,
        body: { ...delegationForm },
      })
    }
    dialog.value = false
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to save delegation'
  }
}

async function setActive(bindingId: string, isActive: boolean) {
  errorText.value = ''
  try {
    await updateDelegation({ bindingId, body: { is_active: isActive } })
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to update delegation'
  }
}

async function removeBinding(bindingId: string) {
  errorText.value = ''
  try {
    await deleteDelegation(bindingId)
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to remove delegation'
  }
}
</script>
