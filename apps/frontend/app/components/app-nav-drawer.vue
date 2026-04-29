<template>
  <div class="nav-drawer-wrapper">

    <v-list density="compact" nav color="primary">
      <!-- Entry tools — no section header -->
      <v-list-item
        v-for="item in entryItems"
        :key="item.to"
        :to="item.to"
        :title="item.title"
        active-class="nav-item--active"
      >
        <template #prepend>
          <v-icon :icon="item.icon" size="20" />
        </template>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Agents -->
      <v-list-subheader>Agents</v-list-subheader>
      <v-list-item
        v-for="item in agentItems"
        :key="item.to"
        :to="item.to"
        :title="item.title"
        active-class="nav-item--active"
        exact
      >
        <template #prepend>
          <v-icon :icon="item.icon" size="20" />
        </template>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Protection -->
      <v-list-subheader>Protection</v-list-subheader>
      <v-list-item
        v-for="item in protectionItems"
        :key="item.to"
        :to="item.to"
        :title="item.title"
        active-class="nav-item--active"
        exact
      >
        <template #prepend>
          <v-icon :icon="item.icon" size="20" />
        </template>
      </v-list-item>

      <v-divider class="my-2" />

      <!-- Settings — no section header -->
      <v-list-item
        v-for="item in systemItems"
        :key="item.to"
        :to="item.to"
        :title="item.title"
        active-class="nav-item--active"
        exact
      >
        <template #prepend>
          <v-icon :icon="item.icon" size="20" />
        </template>
      </v-list-item>
    </v-list>
  </div>
</template>

<script setup lang="ts">
interface NavItem {
  title: string
  icon: string
  to: string
  highlight?: boolean
}

// --- Entry tools (no section header) ---
const entryItems: NavItem[] = [
  { title: 'Playground', icon: 'mdi-play-circle-outline', to: '/playground' },
  { title: 'Compare', icon: 'mdi-compare', to: '/compare' },
  { title: 'Security Scan', icon: 'mdi-shield-search', to: '/red-team' },
]

// --- Agents (agent workspace) ---
const agentItems: NavItem[] = [
  { title: 'Agent Sandbox', icon: 'mdi-flask-outline', to: '/test-agents' },
  { title: 'My Agents', icon: 'mdi-robot-outline', to: '/agents' },
  { title: 'Templates', icon: 'mdi-shape-plus-outline', to: '/agents/templates' },
  { title: 'Agent Traces', icon: 'mdi-timeline-clock-outline', to: '/agent-traces' },
]

// --- Protection (proxy layer) ---
const protectionItems: NavItem[] = [
  { title: 'Policies', icon: 'mdi-shield-lock', to: '/policies' },
  { title: 'Rules', icon: 'mdi-playlist-check', to: '/rules' },
  { title: 'Request Traces', icon: 'mdi-text-box-search-outline', to: '/requests' },
  { title: 'Analytics', icon: 'mdi-chart-bar', to: '/analytics' },
]

// --- System ---
const systemItems: NavItem[] = [
  { title: 'Middleware', icon: 'mdi-transfer-right', to: '/middleware' },
  { title: 'Settings', icon: 'mdi-cog', to: '/settings' },
]
</script>

<style lang="scss" scoped>
:deep(.v-list-item-title) {
  font-size: 16px !important;
  line-height: 1.5 !important;
  padding-bottom: 2px;
}

:deep(.nav-item--active) {
  border-radius: 12px !important;
  background: rgb(var(--v-theme-secondary)) !important;
  color: rgb(var(--v-theme-on-secondary)) !important;

  .v-list-item__overlay {
    opacity: 0 !important;
  }

  .v-icon {
    color: rgb(var(--v-theme-on-primary)) !important;
  }
}

.nav-item--highlight {
  background: rgba(var(--v-theme-primary), 0.08);
  border-radius: 12px;
  border-left: 3px solid rgb(var(--v-theme-primary));
  margin-bottom: 2px;

  :deep(.v-icon) {
    color: rgb(var(--v-theme-primary));
  }

  &.nav-item--active {
    border-left-color: transparent;
  }
}
</style>
