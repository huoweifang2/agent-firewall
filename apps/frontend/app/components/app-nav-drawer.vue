<template>
  <div class="nav-drawer-wrapper">

    <v-list density="compact" nav color="primary">
      <v-list-item
        v-for="item in coreItems"
        :key="item.to"
        :to="item.to"
        :title="item.title"
        active-class="nav-item--active"
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

const coreItems: NavItem[] = [
  { title: 'Attack Playground', icon: 'mdi-shield-search', to: '/red-team' },
  { title: 'Approvals / Audit', icon: 'mdi-shield-check-outline', to: '/approvals' },
  { title: 'OpenClaw Sandbox', icon: 'mdi-flask-outline', to: '/test-agents' },
  { title: 'OpenClaw Agents', icon: 'mdi-robot-outline', to: '/agents' },
  { title: 'Skills & Hooks', icon: 'mdi-transfer-right', to: '/middleware' },
  { title: 'Trace / Audit', icon: 'mdi-timeline-clock-outline', to: '/agent-traces' },
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
