<template>
  <v-container fluid class="guide-page" style="max-width: 980px">
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="navigateTo('/agents')" />
      <div class="ml-2">
        <h1 class="text-h5">Telegram OpenClaw Integration</h1>
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0" />
      </div>
    </div>

    <v-alert type="info" variant="tonal" class="mb-6" icon="mdi-telegram">
      <v-alert-title>Primary runtime path</v-alert-title>
      <p class="mt-1 mb-0">
        Telegram messages enter the Agent-Firewall Telegram Bridge first, then pass through
        proxy scanning, runtime tool gates, OpenClaw skill or MCP providers, and final
        Telegram reply delivery.
      </p>
    </v-alert>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-source-branch" size="22" />
        1. Runtime chain
      </h2>
      <v-sheet rounded class="pa-4 code-block">
        <pre class="text-body-2"><code>Telegram Bot
  -> Agent-Firewall Telegram Bridge
  -> Proxy /v1/scan
  -> agent runtime graph
  -> pre-tool gate
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> trace + audit log
  -> Telegram reply</code></pre>
      </v-sheet>
    </section>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-file-cog-outline" size="22" />
        2. Local config sources
      </h2>
      <v-table density="compact" class="guide-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Used for</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>~/.openclaw/openclaw.json</code></td>
            <td>Telegram bot token/account, OpenClaw agents, model provider, skills, hooks</td>
          </tr>
          <tr>
            <td><code>~/.openclaw/agent-firewall.json</code></td>
            <td>Bridge takeover settings, account allowlist, default policy/model/user role</td>
          </tr>
          <tr>
            <td><code>apps/proxy-service/.env</code></td>
            <td>SQLite database path, proxy scanner settings, local API defaults</td>
          </tr>
          <tr>
            <td><code>apps/agent/.env</code></td>
            <td>Agent runtime port, proxy URL, OpenClaw CLI path, bridge enablement</td>
          </tr>
        </tbody>
      </v-table>
    </section>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-console" size="22" />
        3. Start locally
      </h2>
      <v-sheet rounded class="pa-4 code-block mb-3">
        <pre class="text-body-2"><code>./start-local.sh</code></pre>
      </v-sheet>
      <p class="text-body-2 text-medium-emphasis mb-0">
        The script starts the proxy on <code>:8000</code>, the agent runtime on
        <code>:8002</code>, and the console on <code>:3000</code>. Python services use
        <code>uv</code>; the frontend uses npm.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-message-processing-outline" size="22" />
        4. Protected chat API
      </h2>
      <v-sheet rounded class="pa-4 code-block mb-3">
        <pre class="text-body-2"><code>POST http://localhost:8002/agent/chat
{
  "message": "hello",
  "session_id": "telegram-default-123456",
  "user_role": "customer",
  "policy": "balanced",
  "model": "deepseek-chat"
}</code></pre>
      </v-sheet>
      <p class="text-body-2 text-medium-emphasis mb-3">
        Responses include <code>response</code>, <code>tools_called</code>,
        <code>firewall_decision</code>, <code>agent_trace</code>, and <code>trace</code>.
      </p>
      <v-sheet rounded class="pa-4 code-block">
        <pre class="text-body-2"><code>POST http://localhost:8002/agent/openclaw/direct
{
  "message": "same request",
  "session_id": "compare-session",
  "agent_id": "coder"
}</code></pre>
      </v-sheet>
      <p class="text-body-2 text-medium-emphasis mt-3 mb-0">
        The direct endpoint is only for Compare. Telegram traffic should not use it.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-shield-alert-outline" size="22" />
        5. Approval queue
      </h2>
      <v-table density="compact" class="guide-table mb-3">
        <thead>
          <tr>
            <th>Endpoint</th>
            <th>Purpose</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>POST /v1/interventions</code></td>
            <td>Telegram Bridge creates a pending item for blocked input or tool confirmation</td>
          </tr>
          <tr>
            <td><code>GET /v1/interventions?status=pending</code></td>
            <td>Console lists pending approvals and audit details</td>
          </tr>
          <tr>
            <td><code>PATCH /v1/interventions/{id}</code></td>
            <td>Operator allows or rejects the paused Telegram flow</td>
          </tr>
        </tbody>
      </v-table>
      <p class="text-body-2 text-medium-emphasis mb-0">
        When an item is approved, the agent worker replays the runtime with
        <code>approved_intervention_id</code> and sends the final answer back to Telegram.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-h6 mb-3 d-flex align-center ga-2">
        <v-icon icon="mdi-clipboard-text-clock-outline" size="22" />
        6. Audit fields
      </h2>
      <v-row>
        <v-col v-for="item in auditItems" :key="item.label" cols="12" sm="6" md="4">
          <v-card variant="tonal" class="pa-3 h-100">
            <div class="d-flex align-center ga-2 mb-1">
              <v-icon :icon="item.icon" size="18" />
              <span class="text-subtitle-2">{{ item.label }}</span>
            </div>
            <p class="text-body-2 text-medium-emphasis mb-0">{{ item.description }}</p>
          </v-card>
        </v-col>
      </v-row>
    </section>

    <v-card variant="tonal" color="primary" class="pa-5">
      <div class="d-flex align-center justify-space-between flex-wrap ga-3">
        <div>
          <h3 class="text-h6 mb-1">Console workflow</h3>
          <p class="text-body-2 mb-0">
            Use Attack Playground for adversarial testing, Approvals / Audit for paused
            Telegram traffic, and OpenClaw Agents for protected skill imports.
          </p>
        </div>
        <v-btn color="primary" prepend-icon="mdi-shield-search" to="/red-team">
          Open Playground
        </v-btn>
      </div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
definePageMeta({ title: 'Telegram OpenClaw Integration' })

const breadcrumbs = [
  { title: 'Agents', to: '/agents' },
  { title: 'Integration Guide' },
]

const auditItems = [
  { icon: 'mdi-telegram', label: 'Telegram source', description: 'Account, chat id, session id, and takeover source' },
  { icon: 'mdi-shield-alert', label: 'Firewall decision', description: 'ALLOW, MODIFY, BLOCK, or tool confirmation reason' },
  { icon: 'mdi-tools', label: 'Tool payload', description: 'Provider type, tool name, arguments, and confirmation state' },
  { icon: 'mdi-identifier', label: 'Trace id', description: 'Correlation id linking proxy scans, runtime graph, and approvals' },
  { icon: 'mdi-account-check', label: 'Operator action', description: 'Allow or reject decision with timestamp and note' },
  { icon: 'mdi-send-check', label: 'Telegram reply', description: 'Completion status after approved replay back to the user' },
]
</script>

<style lang="scss" scoped>
.code-block {
  background: rgba(var(--v-theme-surface), 0.6);
  border: 1px solid rgba(var(--v-theme-primary), 0.15);
  overflow-x: auto;
  font-family: monospace;

  pre {
    margin: 0;
    white-space: pre;
  }

  code {
    font-size: 13px;
    line-height: 1.6;
  }
}

.guide-table {
  background: transparent !important;

  th {
    font-weight: 600 !important;
  }
}
</style>
