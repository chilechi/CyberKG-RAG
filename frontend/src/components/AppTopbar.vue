<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <header class="app-topbar">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div class="topbar-actions">
      <label class="global-search">
        <span>⌕</span>
        <input type="search" placeholder="全局搜索（接口预留）" disabled />
      </label>
      <span class="topbar-chip">admin</span>
    </div>
  </header>
</template>
