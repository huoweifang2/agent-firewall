<template>
  <v-container fluid class="agents-page">
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <h1 class="text-h5 mb-1">My Agents</h1>
        <p class="text-body-2 text-medium-emphasis">
          Main agents own their subagents, tools, delegation rules, and traces.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-btn variant="text" icon="mdi-refresh" :loading="isLoading" @click="refetch" />
        <v-btn variant="tonal" prepend-icon="mdi-shape-plus-outline" @click="navigateTo('/agents/templates')">
          Templates
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="navigateTo('/agents/new')">
          New Main Agent
        </v-btn>
      </div>
    </div>

    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="Search agent teams"
      variant="outlined"
      density="compact"
      hide-details
      clearable
      class="mb-4"
      style="max-width: 420px"
    />

    <div v-if="isLoading && !teams.length" class="py-8">
      <v-skeleton-loader v-for="n in 3" :key="n" type="list-item-avatar-three-line" class="mb-2" />
    </div>

    <v-card v-else-if="!teams.length" variant="outlined" class="text-center pa-12">
      <v-icon icon="mdi-account-supervisor-circle-outline" size="72" color="primary" class="mb-4" />
      <h2 class="text-h6 mb-2">No agent teams yet</h2>
      <p class="text-body-2 text-medium-emphasis mb-6">
        Create a coordinator team or start with an empty main agent.
      </p>
      <div class="d-flex justify-center ga-2">
        <v-btn color="primary" prepend-icon="mdi-shape-plus-outline" @click="navigateTo('/agents/templates')">
          Use Template
        </v-btn>
        <v-btn variant="tonal" prepend-icon="mdi-plus" @click="navigateTo('/agents/new')">
          Empty Main Agent
        </v-btn>
      </div>
    </v-card>

    <div v-else class="d-flex flex-column ga-3">
      <v-card
        v-for="team in filteredTeams"
        :key="team.main_agent.id"
        variant="outlined"
        class="agent-team"
      >
        <div class="agent-team__main" @click="navigateTo(`/agents/${team.main_agent.id}`)">
          <div class="d-flex align-center ga-3">
            <v-avatar color="primary" variant="tonal" rounded="sm">
              <v-icon icon="mdi-account-supervisor-circle-outline" />
            </v-avatar>
            <div>
              <div class="d-flex align-center ga-2">
                <h2 class="text-subtitle-1 mb-0">{{ team.main_agent.name }}</h2>
                <v-chip size="x-small" color="primary" variant="tonal">main</v-chip>
                <v-chip size="x-small" :color="rolloutColor(team.main_agent.rollout_mode)" variant="tonal">
                  {{ team.main_agent.rollout_mode }}
                </v-chip>
              </div>
              <p class="text-body-2 text-medium-emphasis mb-0">
                {{ team.main_agent.description || 'No description' }}
              </p>
              <div class="text-caption text-medium-emphasis mt-1">
                {{ team.tools_count }} tools · {{ team.roles_count }} roles · {{ team.skills_count }} skills · {{ team.sub_agents.length }} subagents
              </div>
            </div>
          </div>
          <div class="d-flex ga-1" @click.stop>
            <v-btn size="small" variant="text" icon="mdi-plus" title="Add subagent" @click="openSubAgentDialog(team.main_agent.id)" />
            <v-btn size="small" variant="text" icon="mdi-flask-outline" title="Open sandbox" @click="openSandbox(team.main_agent.id)" />
            <v-btn size="small" variant="text" icon="mdi-pencil" title="Edit" @click="navigateTo(`/agents/${team.main_agent.id}/edit`)" />
          </div>
        </div>

        <v-divider v-if="team.sub_agents.length" />

        <v-list v-if="team.sub_agents.length" density="compact" lines="two" class="py-0">
          <v-list-item
            v-for="sub in team.sub_agents"
            :key="sub.agent.id"
            class="agent-team__sub"
            @click="navigateTo(`/agents/${sub.agent.id}`)"
          >
            <template #prepend>
              <v-icon icon="mdi-subdirectory-arrow-right" color="medium-emphasis" class="mr-1" />
              <v-avatar color="secondary" variant="tonal" rounded="sm" size="32">
                <v-icon icon="mdi-robot-outline" size="18" />
              </v-avatar>
            </template>
            <v-list-item-title>
              <span class="font-weight-medium">{{ sub.agent.name }}</span>
              <v-chip size="x-small" class="ml-2" variant="tonal">subagent</v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ sub.binding?.when_to_delegate || sub.agent.description || 'No delegation rule' }}
            </v-list-item-subtitle>
            <template #append>
              <span class="text-caption text-medium-emphasis">
                {{ sub.tools_count }} tools · {{ sub.skills_count }} skills
              </span>
            </template>
          </v-list-item>
        </v-list>

        <div v-else class="px-4 pb-4 text-body-2 text-medium-emphasis">
          No subagents yet.
        </div>
      </v-card>
    </div>

    <v-dialog v-model="subAgentDialog" max-width="560">
      <v-card>
        <v-card-title>Create Subagent</v-card-title>
        <v-card-text>
          <v-form v-model="subAgentValid">
            <v-text-field
              v-model="subAgentForm.name"
              label="Name"
              variant="outlined"
              :rules="[(v: string) => !!v?.trim() || 'Required']"
            />
            <v-textarea v-model="subAgentForm.description" label="Responsibility" variant="outlined" rows="2" />
            <v-textarea v-model="subAgentForm.when_to_delegate" label="When to delegate" variant="outlined" rows="2" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="subAgentDialog = false">Cancel</v-btn>
          <v-btn color="primary" :disabled="!subAgentValid" :loading="isCreatingSubAgent" @click="createSubAgentFromDialog">
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useAgentTeams } from '~/composables/useAgentTeams'
import type { RolloutMode } from '~/types/wizard'

definePageMeta({ title: 'My Agents' })

const search = ref('')
const selectedMainAgentId = ref<string | null>(null)
const subAgentDialog = ref(false)
const subAgentValid = ref(false)
const subAgentForm = reactive({
  name: '',
  description: '',
  when_to_delegate: '',
})

const { teams, isLoading, refetch, createSubAgent, isCreatingSubAgent } = useAgentTeams()

const filteredTeams = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return teams.value
  return teams.value.filter((team) => {
    const mainMatch = [team.main_agent.name, team.main_agent.description].some(v => (v || '').toLowerCase().includes(q))
    const subMatch = team.sub_agents.some(sub => [sub.agent.name, sub.agent.description, sub.binding?.when_to_delegate]
      .some(v => (v || '').toLowerCase().includes(q)))
    return mainMatch || subMatch
  })
})

const rolloutColor = (mode: RolloutMode) =>
  ({ observe: 'blue', warn: 'amber', enforce: 'green' })[mode] ?? 'grey'

const openSubAgentDialog = (mainAgentId: string) => {
  selectedMainAgentId.value = mainAgentId
  subAgentForm.name = ''
  subAgentForm.description = ''
  subAgentForm.when_to_delegate = ''
  subAgentDialog.value = true
}

const createSubAgentFromDialog = async () => {
  if (!selectedMainAgentId.value) return
  await createSubAgent({
    mainAgentId: selectedMainAgentId.value,
    body: {
      name: subAgentForm.name,
      description: subAgentForm.description,
      when_to_delegate: subAgentForm.when_to_delegate,
      delegation_description: subAgentForm.description,
      template_key: 'manual_subagent',
    },
  })
  subAgentDialog.value = false
}

const openSandbox = (agentId: string) => {
  navigateTo(`/test-agents?agent=${agentId}`)
}
</script>

<style lang="scss" scoped>
.agent-team {
  overflow: hidden;

  &__main {
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 16px;
  }

  &__sub {
    cursor: pointer;
    padding-left: 24px;
  }
}
</style>
