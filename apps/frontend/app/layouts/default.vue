<template>
  <v-app>
    <v-app-bar density="compact" elevation="0" class="app-bar--shadow">
      <v-app-bar-nav-icon
        @click="drawer = !drawer"
      />
      <v-app-bar-title></v-app-bar-title>

      <template #append>
        <health-indicator />
      </template>
    </v-app-bar>

    <v-navigation-drawer v-model="drawer" width="280">
      <app-nav-drawer />
    </v-navigation-drawer>

    <v-main>
      <slot />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const drawer = ref(true)
</script>

<style lang="scss" scoped>
// Ensure main content fills viewport
.v-main {
  min-height: 100vh;
}

.app-bar--shadow {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
}
</style>
