<template>
  <div class="middleware-page pa-4">
    <h1 class="text-h4 mb-4">Middleware Config</h1>
    <p class="mb-6 text-body-1 text-medium-emphasis">
      Manage active Composer toolkits and MCP integrations. 
      <br >
      <strong>Default behavior is zero-protection.</strong> You must explicitly enable Pre-Gate and Post-Gate interception.
    </p>

    <v-card class="mb-4" variant="outlined">
      <v-toolbar color="transparent" density="compact">
        <v-toolbar-title class="text-subtitle-1">Composio Toolkits</v-toolbar-title>
      </v-toolbar>
      <v-divider />
      
      <v-table>
        <thead>
          <tr>
            <th class="text-left">Integration</th>
            <th class="text-center">Enabled</th>
            <th class="text-center">Pre-Tool Gate (Injection & RBAC)</th>
            <th class="text-center">Post-Tool Gate (PII Scrape)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(tool, i) in integrations" :key="i">
            <td>
              <div class="d-flex align-center">
                <v-icon :icon="tool.icon" class="mr-2" color="primary"/>
                <strong>{{ tool.name }}</strong>
              </div>
            </td>
            <td class="text-center">
              <v-switch
                v-model="tool.enabled"
                color="success"
                hide-details
                density="compact"
                class="d-inline-flex"
                @change="saveConfig"
              />
            </td>
            <td class="text-center">
              <v-switch
                v-model="tool.preGate"
                :disabled="!tool.enabled"
                color="warning"
                hide-details
                density="compact"
                class="d-inline-flex"
                @change="saveConfig"
              />
            </td>
            <td class="text-center">
              <v-switch
                v-model="tool.postGate"
                :disabled="!tool.enabled"
                color="warning"
                hide-details
                density="compact"
                class="d-inline-flex"
                @change="saveConfig"
              />
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const integrations = ref([
  { name: 'WEB_SEARCH', icon: 'mdi-web', enabled: false, preGate: false, postGate: false },
  { name: 'GITHUB', icon: 'mdi-github', enabled: false, preGate: false, postGate: false },
  { name: 'SLACK', icon: 'mdi-slack', enabled: false, preGate: false, postGate: false },
  { name: 'FILE', icon: 'mdi-folder', enabled: false, preGate: false, postGate: false },
  { name: 'GMAIL', icon: 'mdi-gmail', enabled: false, preGate: false, postGate: false },
])

onMounted(() => {
  const saved = localStorage.getItem('middleware-config')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      // Merge saved state into the base integrations array
      for (const p of parsed) {
        const existing = integrations.value.find(i => i.name === p.name)
        if (existing) {
          existing.enabled = p.enabled
          existing.preGate = p.preGate
          existing.postGate = p.postGate
        }
      }
    } catch (e) {
      console.error(e)
    }
  }
})

function saveConfig() {
  localStorage.setItem('middleware-config', JSON.stringify(integrations.value))
}
</script>

<style scoped>
.middleware-page {
  max-width: 1000px;
  margin: 0 auto;
}
</style>
