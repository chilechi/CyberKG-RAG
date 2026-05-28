<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchOverviewSummary, type MetricCard, type OverviewSummary } from "../api/overview";

const summary = ref<OverviewSummary | null>(null);
const loading = ref(false);
const error = ref("");

const metrics = computed(() => summary.value?.metrics ?? []);
const dependencies = computed(() => summary.value?.dependencies ?? []);
const entityTypes = computed(() => summary.value?.entity_types ?? []);
const relationTypes = computed(() => summary.value?.relation_types ?? []);
const documentSources = computed(() => summary.value?.document_sources ?? []);
const flowSteps = computed(() => summary.value?.flow_steps ?? []);
const readyCount = computed(() => dependencies.value.filter((item) => item.status === "ok").length);

const metricMap = computed(() => new Map(metrics.value.map((metric) => [metric.key, metric])));

const overviewCards = computed(() => [
  metricMap.value.get("entities"),
  metricMap.value.get("relations"),
  metricMap.value.get("documents"),
  metricMap.value.get("vectors"),
  metricMap.value.get("qa_history"),
].filter(Boolean) as MetricCard[]);

function formatValue(value: number | null | undefined) {
  return value === null || value === undefined ? "--" : value.toLocaleString("zh-CN");
}

function total(items: { count: number }[]) {
  return items.reduce((sum, item) => sum + item.count, 0);
}

async function loadSummary() {
  loading.value = true;
  error.value = "";
  try {
    summary.value = await fetchOverviewSummary();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "系统总览加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="page-grid dashboard-page">
    <section class="metric-grid dashboard-metrics">
      <article v-for="metric in overviewCards" :key="metric.key" class="metric-card compact-card">
        <span class="metric-label">{{ metric.label }}</span>
        <strong>{{ formatValue(metric.value) }}{{ metric.unit }}</strong>
        <small>{{ metric.description }}</small>
      </article>
    </section>

    <section v-if="loading" class="panel state-panel compact-state">正在加载真实统计数据...</section>
    <section v-else-if="error" class="panel state-panel error compact-state">{{ error }}</section>

    <section class="dashboard-main tighter-grid">
      <div class="panel flow-panel">
        <div class="section-heading compact">
          <div>
            <h2>系统架构与流程</h2>
            <p>流程节点来自后端聚合结果，状态随数据库和依赖变化。</p>
          </div>
        </div>
        <div class="flow-line compact-flow">
          <template v-for="(step, index) in flowSteps" :key="step.key">
            <div :class="['flow-step', step.status]">
              <strong>{{ step.label }}</strong>
              <span>{{ step.description }}</span>
              <small>数量：{{ formatValue(step.count) }}</small>
            </div>
            <b v-if="index < flowSteps.length - 1">→</b>
          </template>
        </div>
      </div>

      <div class="panel graph-overview-panel">
        <div class="section-heading compact">
          <div>
            <h2>知识图谱概况</h2>
            <p>实体和关系类型按 PostgreSQL 样例表实时聚合。</p>
          </div>
        </div>
        <div class="kg-summary">
          <div class="kg-core">
            <strong>{{ formatValue(metricMap.get("graph_nodes")?.value) }}</strong>
            <span>图谱节点</span>
          </div>
          <div class="kg-core secondary">
            <strong>{{ formatValue(metricMap.get("graph_relations")?.value) }}</strong>
            <span>图谱关系</span>
          </div>
        </div>
        <div class="legend-block">
          <h3>节点类型</h3>
          <div v-if="entityTypes.length > 0" class="legend-list">
            <span v-for="item in entityTypes" :key="item.key">
              <i></i>{{ item.label }} <b>{{ item.count }}</b>
            </span>
          </div>
          <div v-else class="inline-empty">暂无节点类型数据</div>
        </div>
        <div class="legend-block">
          <h3>关系类型</h3>
          <div v-if="relationTypes.length > 0" class="legend-list relation-list">
            <span v-for="item in relationTypes" :key="item.key">
              <i></i>{{ item.label }} <b>{{ item.count }}</b>
            </span>
          </div>
          <div v-else class="inline-empty">暂无关系类型数据</div>
        </div>
      </div>
    </section>

    <section class="dashboard-bottom tighter-grid">
      <div class="panel">
        <div class="section-heading compact">
          <div>
            <h2>数据来源概况</h2>
            <p>文档片段来源按 PostgreSQL doc_chunks 聚合。</p>
          </div>
        </div>
        <div class="source-table">
          <div class="source-row header">
            <span>来源</span>
            <span>片段数</span>
            <span>占比</span>
          </div>
          <div v-for="item in documentSources" :key="item.key" class="source-row">
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
            <span>{{ total(documentSources) ? Math.round((item.count / total(documentSources)) * 100) : 0 }}%</span>
          </div>
          <div v-if="documentSources.length === 0" class="inline-empty">暂无来源数据</div>
        </div>
      </div>

      <div class="panel">
        <div class="section-heading compact">
          <div>
            <h2>依赖状态</h2>
            <p>{{ readyCount }} / {{ dependencies.length }} 项检查通过</p>
          </div>
          <button class="ghost-button small-button" type="button" @click="loadSummary">刷新</button>
        </div>
        <div class="status-list compact-status-list">
          <div v-for="item in dependencies" :key="item.name" class="status-row">
            <span :class="['status-dot', item.status]"></span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.message }}</small>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
