<template>
  <v-container fluid class="templates-page">
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <h1 class="text-h5 mb-1">Agent Templates</h1>
        <p class="text-body-2 text-medium-emphasis">
          Start from a main agent with coordinated subagents.
        </p>
      </div>
      <v-btn variant="text" icon="mdi-arrow-left" @click="navigateTo('/agents')" />
    </div>

    <v-row>
      <v-col cols="12" md="6" lg="4">
        <v-card variant="outlined" class="template-card">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-account-supervisor-circle-outline" class="mr-2" />
            Coordinator Team
          </v-card-title>
          <v-card-subtitle>Main agent + research, action, and audit subagents</v-card-subtitle>
          <v-card-text>
            <v-list density="compact">
              <v-list-item title="Coordinator Agent" subtitle="Plans, delegates, and summarizes" />
              <v-list-item title="Research Agent" subtitle="Search and source gathering" />
              <v-list-item title="Action Agent" subtitle="External write actions with confirmation" />
              <v-list-item title="Security Auditor" subtitle="Checks output and permission risks" />
            </v-list>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              color="primary"
              prepend-icon="mdi-plus"
              :loading="isCreatingTemplate"
              @click="createCoordinator"
            >
              Create Team
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <v-col cols="12" md="6" lg="4">
        <v-card variant="outlined" class="template-card">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-robot-outline" class="mr-2" />
            Empty Main Agent
          </v-card-title>
          <v-card-subtitle>Manual setup with the existing guided flow</v-card-subtitle>
          <v-card-text>
            Use this when you want to define the main agent, tools, roles, policy, validation, and rollout from scratch.
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="tonal" prepend-icon="mdi-magic-staff" @click="navigateTo('/agents/new')">
              Open Creator
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { useAgentTeams } from '~/composables/useAgentTeams'

definePageMeta({ title: 'Agent Templates' })

const { createTemplate, isCreatingTemplate } = useAgentTeams()

const createCoordinator = async () => {
  const team = await createTemplate({ template_key: 'coordinator_team' })
  navigateTo(`/agents/${team.main_agent.id}`)
}
</script>

<style lang="scss" scoped>
.template-card {
  height: 100%;
}
</style>
