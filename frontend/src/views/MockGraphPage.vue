<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchGraphNeighbors } from "../api/graph";
import type { GraphData } from "../api/mock";
import GraphView from "../components/GraphView.vue";

const graph = ref<GraphData | null>(null);
const loading = ref(false);
const error = ref("");
const entityId = ref("CVE-2021-44228");
const depth = ref(4);

async function loadGraph() {
  if (!entityId.value.trim()) {
    error.value = "请输入实体 ID";
    graph.value = null;
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    graph.value = await fetchGraphNeighbors(entityId.value.trim(), depth.value);
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
        <h2>知识图谱查询</h2>
        <p>从 Neo4j 查询实体邻居和多跳路径</p>
      </div>
    </div>

    <div class="query-row">
      <label>
        实体 ID
        <input v-model="entityId" type="text" placeholder="例如 CVE-2021-44228" @keyup.enter="loadGraph" />
      </label>
      <label>
        深度
        <select v-model.number="depth">
          <option :value="1">1 跳</option>
          <option :value="2">2 跳</option>
          <option :value="3">3 跳</option>
          <option :value="4">4 跳</option>
        </select>
      </label>
      <button class="primary" :disabled="loading" @click="loadGraph">
        {{ loading ? "查询中..." : "查询" }}
      </button>
    </div>

    <div v-if="loading" class="state">正在加载图谱...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="!graph || graph.nodes.length === 0" class="state">暂无图谱数据</div>
    <GraphView v-else :graph="graph" />
  </section>
</template>
