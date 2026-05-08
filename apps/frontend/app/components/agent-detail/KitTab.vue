<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <h3 class="text-subtitle-1">Integration Kit</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Generated single-file examples and runtime scaffolding for this agent.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" :loading="isGenerating" @click="generate">
          Generate
        </v-btn>
        <v-btn v-if="kit" size="small" variant="tonal" prepend-icon="mdi-content-copy" @click="copySelected">
          Copy File
        </v-btn>
        <v-btn v-if="kit" size="small" variant="tonal" prepend-icon="mdi-download" @click="download">
          Download ZIP
        </v-btn>
      </div>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>
    <v-alert v-if="copied" type="success" variant="tonal" density="compact" class="mb-3">
      Copied selected file.
    </v-alert>

    <template v-if="kit?.files && fileNames.length">
      <v-tabs v-model="kitTab" density="compact" class="mb-2">
        <v-tab v-for="fname in fileNames" :key="fname" :value="fname">
          {{ fname }}
        </v-tab>
      </v-tabs>
      <v-card variant="outlined" class="kit-preview pa-3">
        <pre class="text-caption">{{ currentFile }}</pre>
      </v-card>
    </template>
    <div v-else class="text-center py-8 text-medium-emphasis">
      <v-icon icon="mdi-package-variant-closed" size="44" class="mb-2" />
      <div class="text-subtitle-2">No integration kit generated yet</div>
      <div class="text-body-2 mb-4">Generate a kit once tools, roles, and policy are ready.</div>
      <v-btn size="small" color="primary" prepend-icon="mdi-refresh" :loading="isGenerating" @click="generate">
        Generate Kit
      </v-btn>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAgentKit } from '~/composables/useAgentKit'

const props = defineProps<{ agentId: string }>()
const { kit, generate: generateKit, isGenerating, download, copyFile } = useAgentKit(() => props.agentId)

const kitTab = ref('')
const errorText = ref('')
const copied = ref(false)

const fileNames = computed(() => Object.keys(kit.value?.files ?? {}))
const currentFile = computed(() => kit.value?.files?.[kitTab.value] ?? '')

watch(fileNames, (names) => {
  if (!kitTab.value || !names.includes(kitTab.value)) {
    kitTab.value = names[0] ?? ''
  }
}, { immediate: true })

async function generate() {
  errorText.value = ''
  try {
    await generateKit()
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to generate integration kit'
  }
}

async function copySelected() {
  await copyFile(currentFile.value)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1800)
}
</script>

<style scoped>
.kit-preview {
  max-height: 560px;
  overflow: auto;
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.kit-preview pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Fira Code', 'Roboto Mono', monospace;
}
</style>

