<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchDataManagementSummary, type DataManagementSummary } from "../api/dataManagement";

const summary = ref<DataManagementSummary | null>(null);
const loading = ref(false);
const error = ref("");

const metrics = computed(() => summary.value?.metrics ?? []);
const sources = computed(() => summary.value?.sources ?? []);
const importSteps = computed(() => summary.value?.import_steps ?? []);
const recentTasks = computed(() => summary.value?.recent_tasks ?? []);

function formatValue(value: number | null | undefined) {
  return value === null || value === undefined ? "--" : value.toLocaleString("zh-CN");
}

async function loadDataSummary() {
  loading.value = true;
  error.value = "";
  try {
    summary.value = await fetchDataManagementSummary();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "数据管理信息加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadDataSummary);
</script>

<template>
  <div class="page-grid data-page">
    <section class="metric-grid data-metrics">
      <article v-for="metric in metrics" :key="metric.key" class="metric-card compact-card">
        <span class="metric-label">{{ metric.label }}</span>
        <strong>{{ formatValue(metric.value) }}</strong>
        <small>{{ metric.description }}</small>
        <em v-if="metric.status === 'reserved'">接口预留</em>
      </article>
    </section>

    <section v-if="loading" class="panel state-panel compact-state">正在加载数据管理信息...</section>
    <section v-else-if="error" class="panel state-panel error compact-state">{{ error }}</section>

    <section class="data-main tighter-grid">
      <div class="panel">
        <div class="section-heading compact">
          <div>
            <h2>数据导入流程</h2>
            <p>流程数量来自当前数据库和向量集合，不写静态演示值。</p>
          </div>
        </div>
        <div class="import-flow">
          <template v-for="(step, index) in importSteps" :key="step.key">
            <div>
              <strong>{{ index + 1 }}. {{ step.label }}</strong>
              <span>{{ step.description }}</span>
              <small>数量：{{ formatValue(step.count) }}</small>
            </div>
            <b v-if="index < importSteps.length - 1">→</b>
          </template>
        </div>
      </div>

      <div class="panel">
        <div class="section-heading compact">
          <div>
            <h2>最近导入任务</h2>
            <p>任务表尚未实现，后续接入同步任务记录。</p>
          </div>
          <button class="ghost-button small-button" type="button" @click="loadDataSummary">刷新</button>
        </div>
        <div v-if="recentTasks.length === 0" class="empty-table compact-empty">
          <span>暂无真实任务记录</span>
          <small>接口预留：导入任务、同步状态、失败原因</small>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading compact">
        <div>
          <h2>数据源管理</h2>
          <p>按 PostgreSQL 文档片段来源聚合，存储目标来自当前入库链路。</p>
        </div>
      </div>
      <div class="data-table">
        <div class="data-row header">
          <span>数据源名称</span>
          <span>类型</span>
          <span>存储目标</span>
          <span>文档数</span>
          <span>状态</span>
        </div>
        <div v-for="source in sources" :key="source.name" class="data-row">
          <strong>{{ source.name }}</strong>
          <span>{{ source.source_type }}</span>
          <span>{{ source.storage_targets.join(" / ") }}</span>
          <span>{{ source.document_count }}</span>
          <span class="status-text">{{ source.status === "ready" ? "正常" : source.status }}</span>
        </div>
        <div v-if="sources.length === 0" class="empty-table compact-empty">暂无数据源</div>
      </div>
    </section>
  </div>
</template>
