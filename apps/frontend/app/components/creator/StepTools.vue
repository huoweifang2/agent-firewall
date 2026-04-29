<template>
  <v-card flat>
    <v-card-title class="text-h6 d-flex align-center justify-space-between">
      <span>Integration & Tools</span>
    </v-card-title>
    <v-card-subtitle>Select the external tools and integrations this agent can access.</v-card-subtitle>

    <v-card-text class="pt-6">
      <div v-if="isLoading || isSkillsLoading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-row v-else>
        <v-col
          v-for="skill in openClawSkills"
          :key="skill.name"
          cols="12"
          md="6"
          lg="4"
        >
          <v-card
            variant="outlined"
            class="d-flex flex-column"
            style="height: 100%"
            :class="{'bg-primary-lighten-5 border-primary': getToolByName(openClawToolName(skill.name))}"
          >
            <v-card-text class="d-flex align-center justify-space-between">
              <div class="d-flex align-center">
                <v-avatar color="primary" variant="tonal" rounded="sm" class="mr-3">
                  <span class="text-subtitle-2">{{ skill.emoji || 'OC' }}</span>
                </v-avatar>
                <div>
                  <div class="text-subtitle-1 font-weight-medium lh-sm">{{ skill.name }}</div>
                  <div class="text-caption text-medium-emphasis">OpenClaw</div>
                </div>
              </div>
              <v-switch
                :model-value="!!getToolByName(openClawToolName(skill.name))"
                color="success"
                hide-details
                density="compact"
                :disabled="isImportingOpenClaw"
                @update:model-value="toggleSkill(skill.name, $event)"
              />
            </v-card-text>
            <v-card-text class="pt-0 text-body-2 text-medium-emphasis">
              {{ skill.description }}
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useAgentTools, useOpenClawSkills } from '~/composables/useAgentTools'

const props = defineProps<{
  agentId: string
}>()

const emit = defineEmits<{
  valid: [valid: boolean]
}>()

const { tools, isLoading, deleteTool, importOpenClawTools, isImportingOpenClaw } = useAgentTools(() => props.agentId)
const { data: skillsResponse, isLoading: isSkillsLoading } = useOpenClawSkills()

const openClawSkills = computed(() => skillsResponse.value?.items ?? [])

function openClawToolName(skillName: string) {
  const slug = skillName.trim().replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase()
  return `openclaw_${slug || 'skill'}`.slice(0, 64)
}

function getToolByName(name: string) {
  return tools.value.find(t => t.name === name)
}

async function toggleSkill(skillName: string, enabled: boolean) {
  const toolName = openClawToolName(skillName)
  if (enabled) {
    const existing = getToolByName(toolName)
    if (!existing) {
      await importOpenClawTools([skillName])
    }
  } else {
    const existing = getToolByName(toolName)
    if (existing) {
      await deleteTool(existing.id)
    }
  }
}

watch(tools, (t) => emit('valid', t.length > 0), { immediate: true })
</script>
