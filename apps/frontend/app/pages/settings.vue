<template>
  <v-container class="settings-page py-6" style="max-width: 980px;">
    <div class="d-flex align-center justify-space-between mb-5">
      <div>
        <h1 class="text-h5 mb-1">
          <v-icon start>mdi-console</v-icon>
          Runtime Settings
        </h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          OpenClaw, DeepSeek, Telegram, and gateway status for the local Agent-Firewall shell.
        </p>
      </div>
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="runtimeLoading"
        @click="loadOpenClawConfig"
      />
    </div>

    <v-alert
      v-if="openClawError"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      {{ openClawError }}
    </v-alert>

    <v-alert
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      API keys are resolved from local runtime configuration: <code>apps/agent/.env.local</code>,
      <code>apps/proxy-service/.env.local</code>, <code>infra/.env.local</code>, and
      <code>~/.openclaw/openclaw.json</code>. Browser-stored keys are no longer the primary path.
    </v-alert>

    <div class="settings-page__status-grid mb-5">
      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">DeepSeek</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="config?.deepseek_configured ? 'success' : 'warning'" icon="mdi-brain" />
          <span class="text-subtitle-2">{{ config?.deepseek_configured ? 'Configured' : 'Key missing' }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          {{ effectiveModelLabel }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">OpenClaw</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="openClawHealthy ? 'success' : 'warning'" icon="mdi-pulse" />
          <span class="text-subtitle-2">{{ openClawHealthy ? 'Reachable' : 'Needs attention' }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          status {{ yesNo(config?.status_ok) }} · models {{ yesNo(config?.models_ok) }} · agents {{ yesNo(config?.agents_ok) }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">Telegram</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="config?.telegram_enabled ? 'success' : 'grey'" icon="mdi-send" />
          <span class="text-subtitle-2">{{ config?.telegram_enabled ? 'Enabled' : 'Disabled' }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          {{ config?.telegram_accounts ?? 0 }} account{{ (config?.telegram_accounts ?? 0) === 1 ? '' : 's' }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">Telegram Bridge</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="config?.telegram_bridge_running ? 'success' : 'warning'" icon="mdi-shield-link-variant" />
          <span class="text-subtitle-2">{{ config?.telegram_bridge_running ? 'Running' : bridgeStatusLabel }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          {{ config?.telegram_bridge_accounts ?? 0 }} protected account{{ (config?.telegram_bridge_accounts ?? 0) === 1 ? '' : 's' }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">Gateway</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="config?.gateway_token_present ? 'success' : 'warning'" icon="mdi-lan-connect" />
          <span class="text-subtitle-2">{{ config?.gateway_mode || 'unknown' }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          token {{ config?.gateway_token_present ? 'present' : 'missing' }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">Storage</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="runtimeConfig?.database_kind === 'sqlite' ? 'success' : 'warning'" icon="mdi-database-outline" />
          <span class="text-subtitle-2">{{ runtimeConfig?.database_kind || 'loading' }}</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2 text-truncate">
          {{ runtimeConfig?.sqlite_path || runtimeConfig?.database_url_safe || 'runtime pending' }}
        </div>
      </v-sheet>

      <v-sheet border rounded class="pa-4">
        <div class="text-caption text-medium-emphasis mb-2">Local Services</div>
        <div class="d-flex align-center ga-2">
          <v-icon :color="runtimeConfig?.cache_mode === 'memory' ? 'success' : 'info'" icon="mdi-memory" />
          <span class="text-subtitle-2">{{ runtimeConfig?.cache_mode || 'loading' }} cache</span>
        </div>
        <div class="text-caption text-medium-emphasis mt-2">
          Langfuse {{ runtimeConfig?.langfuse_enabled ? 'enabled' : 'disabled' }}
        </div>
      </v-sheet>
    </div>

    <v-sheet border rounded class="pa-4 mb-5">
      <div class="d-flex align-center mb-3">
        <v-icon icon="mdi-robot-outline" size="22" class="mr-2" />
        <span class="text-subtitle-1 font-weight-medium">OpenClaw Runtime</span>
      </div>

      <v-row dense>
        <v-col cols="12" sm="6">
          <v-text-field
            :model-value="config?.openclaw_bin || ''"
            label="OPENCLAW_BIN"
            variant="outlined"
            density="compact"
            hide-details
            readonly
          />
        </v-col>
        <v-col cols="12" sm="6">
          <v-text-field
            :model-value="config?.openclaw_agent_id || ''"
            label="OPENCLAW_AGENT_ID"
            variant="outlined"
            density="compact"
            hide-details
            readonly
          />
        </v-col>
        <v-col cols="12" sm="6">
          <v-text-field
            :model-value="String(config?.openclaw_timeout_seconds ?? '')"
            label="OPENCLAW_TIMEOUT_SECONDS"
            variant="outlined"
            density="compact"
            hide-details
            readonly
          />
        </v-col>
        <v-col cols="12" sm="6">
          <v-text-field
            :model-value="config?.openclaw_plugin_stage_dir || ''"
            label="OPENCLAW_PLUGIN_STAGE_DIR"
            variant="outlined"
            density="compact"
            hide-details
            readonly
          />
        </v-col>
        <v-col cols="12" sm="6">
          <v-switch
            :model-value="config?.openclaw_agent_local ?? false"
            label="OPENCLAW_AGENT_LOCAL"
            color="primary"
            density="compact"
            hide-details
            readonly
          />
        </v-col>
      </v-row>
    </v-sheet>

    <v-alert
      v-if="config?.telegram_bridge_last_error"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-5"
    >
      Telegram Bridge: {{ config.telegram_bridge_last_error }}
    </v-alert>

    <v-sheet border rounded class="pa-4">
      <div class="d-flex align-center mb-3">
        <v-icon icon="mdi-shield-key-outline" size="22" class="mr-2" />
        <span class="text-subtitle-1 font-weight-medium">Legacy Browser Overrides</span>
      </div>
      <p class="text-body-2 text-medium-emphasis mb-3">
        These keys are optional development overrides. The OpenClaw-first runtime should work without them when server-side DeepSeek is configured.
      </p>

      <div v-if="!keys.length" class="text-caption text-medium-emphasis">
        No browser API key overrides are stored.
      </div>

      <v-list v-else density="compact" class="pa-0">
        <v-list-item
          v-for="key in keys"
          :key="key.provider"
          :title="providerLabel(key.provider)"
          :subtitle="`${key.maskedKey} · ${key.remembered ? 'saved locally' : 'session only'}`"
        >
          <template #prepend>
            <v-icon icon="mdi-key-variant" />
          </template>
          <template #append>
            <v-btn
              icon="mdi-delete-outline"
              size="small"
              variant="text"
              @click="removeKey(key.provider)"
            />
          </template>
        </v-list-item>
      </v-list>
    </v-sheet>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useApiKeys } from '~/composables/useApiKeys'
import { agentService } from '~/services/agentService'
import { api } from '~/services/api'

definePageMeta({ title: 'Runtime Settings' })

const { keys, removeKey } = useApiKeys()
const runtimeLoading = ref(false)
const openClawError = ref('')
const config = ref<Awaited<ReturnType<typeof agentService.getOpenClawConfig>> | null>(null)
const runtimeConfig = ref<{
  database_kind: string
  database_url_safe: string
  sqlite_path?: string | null
  cache_mode: string
  redis_configured: boolean
  langfuse_enabled: boolean
} | null>(null)

const openClawHealthy = computed(() =>
  !!config.value?.status_ok && !!config.value?.models_ok && !!config.value?.agents_ok,
)

const effectiveModelLabel = computed(() => {
  if (!config.value) return 'loading model configuration'
  const model = config.value.default_model_prefix
    ? `${config.value.default_model_prefix}/${config.value.default_model}`.replace(/\/deepseek\//, '/')
    : config.value.default_model
  return model
})

const bridgeStatusLabel = computed(() => {
  if (!config.value?.telegram_bridge_enabled) return 'Disabled'
  return 'Stopped'
})

onMounted(() => {
  loadOpenClawConfig()
})

function yesNo(value?: boolean) {
  return value ? 'ok' : 'missing'
}

function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    deepseek: 'DeepSeek',
  }
  return labels[provider] ?? provider
}

async function loadOpenClawConfig() {
  runtimeLoading.value = true
  openClawError.value = ''
  try {
    const [openClawConfig, runtimeResponse] = await Promise.all([
      agentService.getOpenClawConfig(),
      api.get('/v1/runtime/config'),
    ])
    config.value = openClawConfig
    runtimeConfig.value = runtimeResponse.data
    if (config.value.error) {
      openClawError.value = config.value.error
    }
  } catch (err) {
    openClawError.value = err instanceof Error
      ? err.message
      : (err as { message?: string })?.message || 'Agent runtime is not reachable'
  } finally {
    runtimeLoading.value = false
  }
}
</script>

<style scoped>
.settings-page__status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}

code {
  font-size: 0.8em;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}

@media (max-width: 900px) {
  .settings-page__status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .settings-page__status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
