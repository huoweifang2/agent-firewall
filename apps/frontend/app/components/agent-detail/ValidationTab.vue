<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <h3 class="text-subtitle-1">Validation</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Run deterministic validation packs against the generated config.
        </p>
      </div>
      <div class="d-flex align-center ga-2">
        <v-select
          v-model="pack"
          :items="packItems"
          label="Pack"
          density="compact"
          variant="outlined"
          hide-details
          style="width: 220px"
        />
        <v-btn size="small" color="primary" prepend-icon="mdi-play" :loading="isRunning" @click="runSelected">
          {{ latest ? 'Re-run' : 'Run' }}
        </v-btn>
      </div>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>

    <template v-if="latest">
      <v-card
        :color="latest.passed === latest.total ? 'success' : 'error'"
        variant="tonal"
        class="mb-4 pa-3"
      >
        <div class="d-flex flex-wrap align-center justify-space-between ga-3">
          <div>
            <div class="text-h4 font-weight-bold">{{ latest.passed }}/{{ latest.total }}</div>
            <div>{{ latest.passed === latest.total ? 'All tests passed' : `${latest.failed} failed` }}</div>
          </div>
          <div class="text-caption">
            {{ latest.pack }} v{{ latest.pack_version }} · {{ formatTime(latest.created_at) }}
          </div>
        </div>
      </v-card>

      <div class="d-flex flex-wrap ga-2 mb-4">
        <v-chip
          v-for="[category, item] in Object.entries(categoryBreakdown)"
          :key="category"
          size="small"
          variant="tonal"
          :color="item.passed === item.total ? 'success' : 'warning'"
        >
          {{ category }} {{ item.passed }}/{{ item.total }}
        </v-chip>
      </div>

      <v-table density="compact">
        <thead>
          <tr>
            <th>Test</th>
            <th>Category</th>
            <th>Expected</th>
            <th>Actual</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(test, index) in validationTests" :key="`${test.name}-${index}`">
            <td>
              <div class="d-flex align-center ga-2">
                <v-icon :icon="test.passed ? 'mdi-check-circle' : 'mdi-close-circle'" :color="test.passed ? 'success' : 'error'" size="18" />
                <div>
                  <div class="font-weight-medium">{{ test.name }}</div>
                  <div v-if="test.recommendation" class="text-caption text-warning">{{ test.recommendation }}</div>
                </div>
              </div>
            </td>
            <td><v-chip size="x-small" variant="outlined">{{ test.category }}</v-chip></td>
            <td>{{ test.expected }}</td>
            <td>{{ test.actual }}</td>
            <td>{{ test.duration_ms }}ms</td>
          </tr>
        </tbody>
      </v-table>
    </template>

    <div v-else class="text-center py-8 text-medium-emphasis">
      <v-icon icon="mdi-clipboard-check-outline" size="44" class="mb-2" />
      <div class="text-subtitle-2">No validation runs yet</div>
      <div class="text-body-2 mb-4">Generate config first, then run the basic pack.</div>
      <v-btn size="small" color="primary" prepend-icon="mdi-play" :loading="isRunning" @click="runSelected">
        Run Validation
      </v-btn>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAgentValidation } from '~/composables/useAgentValidation'

const props = defineProps<{ agentId: string }>()
const { latest, run, isRunning } = useAgentValidation(() => props.agentId)

const pack = ref('basic')
const errorText = ref('')
const packItems = [
  { title: 'Basic deterministic pack', value: 'basic' },
  { title: 'Advanced red-team pack (coming later)', value: 'advanced', props: { disabled: true } },
  { title: 'Production regression pack (coming later)', value: 'production', props: { disabled: true } },
]

interface ValidationCategoryItem {
  passed: number
  total: number
}

const validationTests = computed(() => latest.value?.results?.tests ?? [])
const categoryBreakdown = computed<Record<string, ValidationCategoryItem>>(() => {
  const value = latest.value?.results?.categories
  return value && typeof value === 'object' ? value as Record<string, ValidationCategoryItem> : {}
})

async function runSelected() {
  errorText.value = ''
  try {
    await run(pack.value)
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Validation failed. Generate config first and try again.'
  }
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : 'unknown'
}
</script>
