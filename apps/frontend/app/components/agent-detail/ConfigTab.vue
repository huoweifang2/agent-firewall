<template>
  <v-card variant="outlined" class="pa-4">
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <h3 class="text-subtitle-1">Generated Configuration</h3>
        <p class="text-body-2 text-medium-emphasis mb-0">
          RBAC, limits, and policy YAML generated from the agent control-plane state.
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" :loading="isGenerating" @click="generate">
          Generate
        </v-btn>
        <v-btn v-if="config" size="small" variant="tonal" prepend-icon="mdi-content-copy" @click="copyCurrent">
          Copy
        </v-btn>
        <v-btn v-if="config" size="small" variant="tonal" prepend-icon="mdi-download" @click="downloadConfig">
          Download
        </v-btn>
      </div>
    </div>

    <v-alert v-if="errorText" type="error" variant="tonal" density="compact" class="mb-3" closable @click:close="errorText = ''">
      {{ errorText }}
    </v-alert>
    <v-alert v-if="copied" type="success" variant="tonal" density="compact" class="mb-3">
      Copied to clipboard.
    </v-alert>

    <template v-if="config">
      <v-tabs v-model="configTab" density="compact" class="mb-2">
        <v-tab value="rbac">RBAC</v-tab>
        <v-tab value="limits">Limits</v-tab>
        <v-tab value="policy">Policy</v-tab>
      </v-tabs>
      <v-card variant="outlined" class="config-preview pa-3">
        <pre class="text-caption">{{ configContent }}</pre>
      </v-card>
    </template>
    <div v-else class="text-center py-8 text-medium-emphasis">
      <v-icon icon="mdi-file-cog-outline" size="44" class="mb-2" />
      <div class="text-subtitle-2">No configuration generated yet</div>
      <div class="text-body-2 mb-4">Generate config before validation or runtime integration.</div>
      <v-btn size="small" color="primary" prepend-icon="mdi-refresh" :loading="isGenerating" @click="generate">
        Generate Config
      </v-btn>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAgentConfig } from '~/composables/useAgentConfig'

const props = defineProps<{ agentId: string }>()
const { config, generate: generateConfig, isGenerating, downloadConfig } = useAgentConfig(() => props.agentId)

const configTab = ref('rbac')
const errorText = ref('')
const copied = ref(false)

const configContent = computed(() => {
  if (!config.value) return ''
  const c = config.value as unknown as Record<string, string>
  const map: Record<string, string> = {
    rbac: c.rbac_yaml ?? '',
    limits: c.limits_yaml ?? '',
    policy: c.policy_yaml ?? '',
  }
  return map[configTab.value] ?? ''
})

async function generate() {
  errorText.value = ''
  try {
    await generateConfig()
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Failed to generate config'
  }
}

async function copyCurrent() {
  await navigator.clipboard.writeText(configContent.value)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1800)
}
</script>

<style scoped>
.config-preview {
  max-height: 520px;
  overflow: auto;
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.config-preview pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Fira Code', 'Roboto Mono', monospace;
}
</style>

