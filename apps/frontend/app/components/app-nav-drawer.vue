<template>
  <div class="nav-drawer-wrapper">
    <div class="nav-brand px-4 py-4">
      <div class="text-subtitle-1 font-weight-bold">Agent-Firewall</div>
      <div class="text-caption text-medium-emphasis">Local control console</div>
    </div>

    <v-divider />

    <v-list density="compact" nav color="primary" class="py-2">
      <template v-for="group in groups" :key="group.title">
        <v-list-subheader class="nav-group">{{ group.title }}</v-list-subheader>
        <v-list-item
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          :title="item.title"
          :class="{ 'nav-item--highlight': item.highlight }"
          active-class="nav-item--active"
        >
          <template #prepend>
            <v-icon :icon="item.icon" size="20" />
          </template>
        </v-list-item>
      </template>
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

const coreItems: NavItem[] = [
  { title: 'Dashboard', icon: 'mdi-view-dashboard-outline', to: '/' },
  { title: 'Attack Playground', icon: 'mdi-shield-search', to: '/red-team', highlight: true },
  { title: 'Playground', icon: 'mdi-chat-processing-outline', to: '/playground' },
  { title: 'Compare', icon: 'mdi-compare-horizontal', to: '/compare' },
]

const agentItems: NavItem[] = [
  { title: 'OpenClaw Sandbox', icon: 'mdi-flask-outline', to: '/test-agents' },
  { title: 'Bot Agents', icon: 'mdi-robot-outline', to: '/agents' },
  { title: 'Skills & Hooks', icon: 'mdi-transfer-right', to: '/middleware' },
]

const operationsItems: NavItem[] = [
  { title: 'Approvals / Audit', icon: 'mdi-shield-check-outline', to: '/approvals' },
  { title: 'Trace / Audit', icon: 'mdi-timeline-clock-outline', to: '/agent-traces' },
  { title: 'Requests', icon: 'mdi-format-list-bulleted-square', to: '/requests' },
  { title: 'Analytics', icon: 'mdi-chart-box-outline', to: '/analytics' },
]

const policyItems: NavItem[] = [
  { title: 'Policies', icon: 'mdi-shield-cog-outline', to: '/policies' },
  { title: 'Rules', icon: 'mdi-ruler-square-compass', to: '/rules' },
]

const groups = [
  { title: 'Workflows', items: coreItems },
  { title: 'Agents', items: agentItems },
  { title: 'Operations', items: operationsItems },
  { title: 'Policy', items: policyItems },
]
</script>

<style lang="scss" scoped>
:deep(.v-list-item-title) {
  font-size: 14px !important;
  line-height: 1.5 !important;
  padding-bottom: 2px;
}

.nav-brand {
  min-height: 72px;
}

.nav-group {
  min-height: 28px;
  padding-inline-start: 18px !important;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

:deep(.nav-item--active) {
  border-radius: 8px !important;
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
