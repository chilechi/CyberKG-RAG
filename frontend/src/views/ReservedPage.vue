<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchPublicSettings, fetchReservedApi, type ReservedApiResponse } from "../api/placeholders";

const props = defineProps<{
  title: string;
  description: string;
  endpoint: string;
  settings?: boolean;
}>();

const data = ref<ReservedApiResponse | null>(null);
const publicSettings = ref<Record<string, unknown> | null>(null);
const loading = ref(false);
const error = ref("");

async function loadReservedData() {
  loading.value = true;
  error.value = "";
  try {
    if (props.settings) {
      publicSettings.value = await fetchPublicSettings();
      data.value = null;
    } else {
      data.value = await fetchReservedApi(props.endpoint);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "预留接口加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadReservedData);
</script>

<template>
  <section class="panel reserved-page">
    <div class="section-heading">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <button class="ghost-button" type="button" @click="loadReservedData">刷新</button>
    </div>

    <div v-if="loading" class="state-panel">正在请求接口...</div>
    <div v-else-if="error" class="state-panel error">{{ error }}</div>
    <div v-else-if="settings && publicSettings" class="settings-grid">
      <div v-for="(value, key) in publicSettings" :key="key">
        <span>{{ key }}</span>
        <strong>{{ value }}</strong>
      </div>
    </div>
    <div v-else class="reserved-empty">
      <strong>{{ data?.message ?? "接口预留" }}</strong>
      <p>这里不会写静态演示数据，等后端功能完成后直接渲染接口返回内容。</p>
      <small>接口：{{ endpoint }}</small>
    </div>
  </section>
</template>
