<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchMockGraph, type GraphData } from "../api/mock";
import GraphView from "../components/GraphView.vue";

const graph = ref<GraphData | null>(null);
const loading = ref(false);
const error = ref("");

async function loadGraph() {
  loading.value = true;
  error.value = "";
  try {
    graph.value = await fetchMockGraph();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "图谱数据加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadGraph);
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div>
        <h2>样例知识图谱</h2>
        <p>CVE → CWE → CAPEC → ATT&CK 的 mock 路径</p>
      </div>
      <button class="primary" @click="loadGraph">刷新</button>
    </div>

    <div v-if="loading" class="state">正在加载图谱...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="!graph || graph.nodes.length === 0" class="state">暂无图谱数据</div>
    <GraphView v-else :graph="graph" />
  </section>
</template>
