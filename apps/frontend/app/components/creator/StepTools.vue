<template>
  <v-card flat>
    <v-card-title class="text-h6 d-flex align-center justify-space-between">
      <span>Integration & Tools</span>
    </v-card-title>
    <v-card-subtitle>Select the external tools and integrations this agent can access.</v-card-subtitle>

    <v-card-text class="pt-6">
      <div v-if="isLoading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-row v-else>
        <v-col
          v-for="app in PREDEFINED_APPS"
          :key="app.name"
          cols="12"
          md="6"
          lg="4"
        >
          <v-card
            variant="outlined"
            class="d-flex flex-column"
            style="height: 100%"
            :class="{'bg-primary-lighten-5 border-primary': getToolByName(app.name)}"
          >
            <v-card-text class="d-flex align-center justify-space-between">
              <div class="d-flex align-center">
                <v-avatar color="primary" variant="tonal" rounded="sm" class="mr-3">
                  <v-icon :icon="app.icon" size="24" />
                </v-avatar>
                <div>
                  <div class="text-subtitle-1 font-weight-medium lh-sm">{{ app.name }}</div>
                  <div class="text-caption text-medium-emphasis">{{ app.category }}</div>
                </div>
              </div>
              <v-switch
                :model-value="!!getToolByName(app.name)"
                color="success"
                hide-details
                density="compact"
                @update:model-value="toggleApp(app, $event)"
              />
            </v-card-text>
            <v-card-text class="pt-0 text-body-2 text-medium-emphasis">
              {{ app.description }}
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAgentTools } from '~/composables/useAgentTools'

const props = defineProps<{
  agentId: string
}>()

const emit = defineEmits<{
  valid: [valid: boolean]
}>()

const { tools, isLoading, createTool, deleteTool, refetch } = useAgentTools(() => props.agentId)

const PREDEFINED_APPS = [
  { name: 'WEB_SEARCH', icon: 'mdi-web', category: 'Search', description: 'Search the web using DuckDuckGo.', sensitivity: 'low', access_type: 'read' },
  { name: 'GITHUB', icon: 'mdi-github', category: 'Composio', description: 'Interact with GitHub repositories and issues.', sensitivity: 'medium', access_type: 'write' },
  { name: 'SLACK', icon: 'mdi-slack', category: 'Composio', description: 'Send and read messages in Slack workspace.', sensitivity: 'medium', access_type: 'write' },
  { name: 'FILE', icon: 'mdi-folder', category: 'Composio', description: 'Read and write local or remote files.', sensitivity: 'high', access_type: 'write' },
  { name: 'GMAIL', icon: 'mdi-gmail', category: 'Composio', description: 'Manage and send emails using Gmail.', sensitivity: 'high', access_type: 'write' },
  { name: 'CALENDAR', icon: 'mdi-calendar', category: 'Composio', description: 'Manage calendar events.', sensitivity: 'medium', access_type: 'write' },
]

function getToolByName(name: string) {
  return tools.value.find(t => t.name === name)
}

async function toggleApp(app: typeof PREDEFINED_APPS[0], enabled: boolean) {
  if (enabled) {
    const existing = getToolByName(app.name)
    if (!existing) {
      await createTool({
        name: app.name,
        description: app.description,
        sensitivity: app.sensitivity as any,
        access_type: app.access_type as any,
        category: app.category,
        returns_pii: false,
        returns_secrets: false,
        arg_schema: null,
      })
    }
  } else {
    const existing = getToolByName(app.name)
    if (existing) {
      await deleteTool(existing.id)
    }
  }
}

watch(tools, (t) => emit('valid', t.length > 0), { immediate: true })
</script>
