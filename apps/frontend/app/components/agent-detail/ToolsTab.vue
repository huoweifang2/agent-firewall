<template>
  <v-card variant="outlined">
    <div class="pa-4 d-flex align-center justify-space-between ga-3">
      <div>
        <h3 class="text-subtitle-1">Tools</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Register runtime tools, sensitivity, access type, PII/secrets handling, schemas, and rate limits.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreate">Add Tool</v-btn>
        <v-btn size="small" variant="tonal" prepend-icon="mdi-import" @click="importDialog = true">Import OpenClaw</v-btn>
        <v-btn size="small" variant="text" icon="mdi-refresh" :loading="isLoading" @click="refetch" />
      </div>
    </div>
    <v-divider />

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="ma-4" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <v-data-table
      v-if="tools.length"
      :headers="headers"
      :items="tools"
      density="compact"
      items-per-page="15"
    >
      <template #item.name="{ item }">
        <div class="font-weight-medium">{{ item.name }}</div>
        <div class="text-caption text-medium-emphasis">{{ item.description || 'No description' }}</div>
      </template>
      <template #item.access_type="{ item }">
        <v-chip size="x-small" variant="tonal">{{ item.access_type }}</v-chip>
      </template>
      <template #item.sensitivity="{ item }">
        <v-chip :color="sensitivityColor(item.sensitivity)" size="x-small" variant="tonal">
          {{ item.sensitivity }}
        </v-chip>
      </template>
      <template #item.flags="{ item }">
        <div class="d-flex flex-wrap ga-1">
          <v-chip v-if="item.requires_confirmation" size="x-small" color="warning" variant="tonal">confirm</v-chip>
          <v-chip v-if="item.returns_pii" size="x-small" color="error" variant="tonal">PII</v-chip>
          <v-chip v-if="item.returns_secrets" size="x-small" color="error" variant="tonal">secrets</v-chip>
        </div>
      </template>
      <template #item.rate_limit="{ item }">
        {{ item.rate_limit ?? '—' }}
      </template>
      <template #item.actions="{ item }">
        <v-btn size="small" variant="text" icon="mdi-pencil" @click="openEdit(item)" />
        <v-btn size="small" variant="text" icon="mdi-delete" color="error" :loading="isDeleting" @click="removeTool(item.id)" />
      </template>
    </v-data-table>

    <div v-else class="text-center py-10 text-medium-emphasis">
      <v-icon icon="mdi-wrench-outline" size="44" class="mb-2" />
      <div class="text-subtitle-2">No tools registered</div>
      <div class="text-body-2 mb-4">Add a tool manually or import eligible OpenClaw skills.</div>
      <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreate">Add Tool</v-btn>
    </div>

    <v-dialog v-model="toolDialog" max-width="760">
      <v-card>
        <v-card-title>{{ editing ? 'Edit Tool' : 'Add Tool' }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.name" label="Name" variant="outlined" />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.category" label="Category" variant="outlined" />
            </v-col>
            <v-col cols="12">
              <v-textarea v-model="form.description" label="Description" variant="outlined" rows="2" />
            </v-col>
            <v-col cols="12" md="6">
              <v-select v-model="form.access_type" :items="accessTypes" label="Access Type" variant="outlined" />
            </v-col>
            <v-col cols="12" md="6">
              <v-select v-model="form.sensitivity" :items="sensitivities" label="Sensitivity" variant="outlined" />
            </v-col>
            <v-col cols="12" md="4">
              <v-switch v-model="form.returns_pii" label="Returns PII" color="error" hide-details />
            </v-col>
            <v-col cols="12" md="4">
              <v-switch v-model="form.returns_secrets" label="Returns Secrets" color="error" hide-details />
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field v-model.number="form.rate_limit" type="number" label="Rate Limit" variant="outlined" clearable />
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="argSchemaText"
                label="Argument Schema JSON"
                variant="outlined"
                rows="6"
                auto-grow
                spellcheck="false"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="toolDialog = false">Cancel</v-btn>
          <v-btn color="primary" :disabled="!form.name.trim()" :loading="isCreating || isUpdating" @click="saveTool">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="importDialog" max-width="760">
      <v-card>
        <v-card-title>Import OpenClaw Skills</v-card-title>
        <v-card-text>
          <v-alert v-if="skillsError" type="warning" variant="tonal" density="compact" class="mb-3">
            Could not load OpenClaw skills. Check runtime configuration.
          </v-alert>
          <v-select
            v-model="selectedSkills"
            :items="skillItems"
            :loading="skillsLoading"
            item-title="title"
            item-value="value"
            label="Eligible skills"
            variant="outlined"
            chips
            multiple
          />
          <v-list v-if="selectedSkillDetails.length" density="compact" lines="two" border rounded>
            <v-list-item
              v-for="skill in selectedSkillDetails"
              :key="skill.name"
              :title="skill.name"
              :subtitle="skill.description || 'No description'"
            />
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="importDialog = false">Cancel</v-btn>
          <v-btn color="primary" :disabled="!selectedSkills.length" :loading="isImportingOpenClaw" @click="importSkills">
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useAgentTools, useOpenClawSkills } from '~/composables/useAgentTools'
import type { AccessType, Sensitivity, ToolRead } from '~/types/agentControl'

const props = defineProps<{ agentId: string }>()

const {
  tools,
  isLoading,
  refetch,
  createTool,
  updateTool,
  deleteTool,
  importOpenClawTools,
  isCreating,
  isUpdating,
  isDeleting,
  isImportingOpenClaw,
} = useAgentTools(() => props.agentId)
const { data: skillsData, isLoading: skillsLoading, error: skillsError } = useOpenClawSkills()

const headers = [
  { title: 'Tool', key: 'name' },
  { title: 'Access', key: 'access_type', width: 100 },
  { title: 'Sensitivity', key: 'sensitivity', width: 120 },
  { title: 'Flags', key: 'flags', width: 180 },
  { title: 'Rate', key: 'rate_limit', width: 80 },
  { title: '', key: 'actions', width: 110, sortable: false },
]

const accessTypes: AccessType[] = ['read', 'write']
const sensitivities: Sensitivity[] = ['low', 'medium', 'high', 'critical']

const toolDialog = ref(false)
const importDialog = ref(false)
const editing = ref<ToolRead | null>(null)
const argSchemaText = ref('')
const selectedSkills = ref<string[]>([])
const errorText = ref('')

const form = reactive({
  name: '',
  description: '',
  category: '',
  access_type: 'read' as AccessType,
  sensitivity: 'low' as Sensitivity,
  returns_pii: false,
  returns_secrets: false,
  rate_limit: null as number | null,
})

const skillItems = computed(() => (skillsData.value?.items ?? []).map(skill => ({
  title: `${skill.name}${skill.disabled ? ' (disabled)' : ''}`,
  value: skill.name,
  props: { disabled: skill.disabled || !skill.eligible },
})))

const selectedSkillDetails = computed(() => {
  const set = new Set(selectedSkills.value)
  return (skillsData.value?.items ?? []).filter(skill => set.has(skill.name))
})

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  form.category = ''
  form.access_type = 'read'
  form.sensitivity = 'low'
  form.returns_pii = false
  form.returns_secrets = false
  form.rate_limit = null
  argSchemaText.value = ''
  toolDialog.value = true
}

function openEdit(tool: ToolRead) {
  editing.value = tool
  form.name = tool.name
  form.description = tool.description
  form.category = tool.category ?? ''
  form.access_type = tool.access_type
  form.sensitivity = tool.sensitivity
  form.returns_pii = tool.returns_pii
  form.returns_secrets = tool.returns_secrets
  form.rate_limit = tool.rate_limit
  argSchemaText.value = tool.arg_schema ? JSON.stringify(tool.arg_schema, null, 2) : ''
  toolDialog.value = true
}

function parseArgSchema() {
  if (!argSchemaText.value.trim()) return null
  return JSON.parse(argSchemaText.value)
}

async function saveTool() {
  errorText.value = ''
  try {
    const body = {
      name: form.name.trim(),
      description: form.description,
      category: form.category || null,
      access_type: form.access_type,
      sensitivity: form.sensitivity,
      returns_pii: form.returns_pii,
      returns_secrets: form.returns_secrets,
      rate_limit: form.rate_limit,
      arg_schema: parseArgSchema(),
    }
    if (editing.value) {
      await updateTool({ toolId: editing.value.id, body })
    } else {
      await createTool(body)
    }
    toolDialog.value = false
  } catch (err) {
    errorText.value = err instanceof SyntaxError ? 'Argument schema must be valid JSON' : err instanceof Error ? err.message : 'Failed to save tool'
  }
}

async function removeTool(toolId: string) {
  errorText.value = ''
  try {
    await deleteTool(toolId)
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to delete tool'
  }
}

async function importSkills() {
  errorText.value = ''
  try {
    await importOpenClawTools(selectedSkills.value)
    selectedSkills.value = []
    importDialog.value = false
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to import OpenClaw skills'
  }
}

function sensitivityColor(s: Sensitivity) {
  return ({ low: 'green', medium: 'amber', high: 'orange', critical: 'red' })[s] ?? 'grey'
}
</script>

