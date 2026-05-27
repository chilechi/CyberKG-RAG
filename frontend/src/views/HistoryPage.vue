<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { deleteHistoryItem, fetchHistory, fetchHistoryStats, type HistoryItem, type HistoryStats } from "../api/history";

const items = ref<HistoryItem[]>([]);
const stats = ref<HistoryStats | null>(null);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const keyword = ref("");
const loading = ref(false);
const error = ref("");

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function formatPercent(value: number | null | undefined) {
  return value === null || value === undefined ? "--" : `${Math.round(value * 100)}%`;
}

function formatMs(value: number | null | undefined) {
  return value === null || value === undefined ? "--" : `${(value / 1000).toFixed(2)}s`;
}

async function loadHistory() {
  loading.value = true;
  error.value = "";
  try {
    const [historyData, statsData] = await Promise.all([
      fetchHistory(page.value, pageSize.value, keyword.value.trim()),
      fetchHistoryStats(),
    ]);
    items.value = historyData.items;
    total.value = historyData.total;
    stats.value = statsData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "问答历史加载失败";
  } finally {
    loading.value = false;
  }
}

async function removeItem(id: number) {
  await deleteHistoryItem(id);
  if (items.value.length === 1 && page.value > 1) {
    page.value -= 1;
  }
  await loadHistory();
}

function search() {
  page.value = 1;
  void loadHistory();
}

function goPage(nextPage: number) {
  page.value = Math.min(Math.max(nextPage, 1), totalPages.value);
  void loadHistory();
}

onMounted(loadHistory);
</script>

<template>
  <div class="page-grid history-page">
    <section class="history-toolbar panel">
      <label class="field wide">
        <span>搜索问题关键词</span>
        <input v-model="keyword" type="search" placeholder="输入漏洞、CVE、攻击技术等关键词" @keyup.enter="search" />
      </label>
      <button class="primary small-button" :disabled="loading" type="button" @click="search">
        {{ loading ? "查询中..." : "查询" }}
      </button>
      <button class="ghost-button small-button" type="button" @click="keyword = ''; search()">重置</button>
    </section>

    <section class="metric-grid history-metrics">
      <article class="metric-card compact-card">
        <span class="metric-label">总问答次数</span>
        <strong>{{ stats?.total ?? "--" }}</strong>
        <small>来自 qa_history</small>
      </article>
      <article class="metric-card compact-card">
        <span class="metric-label">KG-RAG 问答数</span>
        <strong>{{ stats?.kg_rag_count ?? "--" }}</strong>
        <small>按 mode 统计</small>
      </article>
      <article class="metric-card compact-card">
        <span class="metric-label">平均置信度</span>
        <strong>{{ formatPercent(stats?.avg_confidence) }}</strong>
        <small>历史记录平均值</small>
      </article>
      <article class="metric-card compact-card">
        <span class="metric-label">平均耗时</span>
        <strong>{{ formatMs(stats?.avg_elapsed_ms) }}</strong>
        <small>后端生成耗时</small>
      </article>
    </section>

    <section class="panel">
      <div class="section-heading compact">
        <div>
          <h2>问答历史记录</h2>
          <p>每次调用智能问答接口后自动写入 PostgreSQL。</p>
        </div>
        <span class="panel-badge">共 {{ total }} 条</span>
      </div>

      <div v-if="loading" class="state-panel compact-state">正在加载问答历史...</div>
      <div v-else-if="error" class="state-panel error compact-state">{{ error }}</div>
      <div v-else-if="items.length === 0" class="empty-table compact-empty">
        <span>暂无问答历史</span>
        <small>先在“智能问答”页提交一个问题，这里会自动出现记录。</small>
      </div>
      <div v-else class="history-table">
        <div class="history-row header">
          <span>问题</span>
          <span>模式</span>
          <span>置信度</span>
          <span>耗时</span>
          <span>证据</span>
          <span>时间</span>
          <span>操作</span>
        </div>
        <div v-for="item in items" :key="item.id" class="history-row">
          <div class="question-cell">
            <strong>{{ item.question }}</strong>
            <small>{{ item.answer }}</small>
          </div>
          <span class="mode-pill">{{ item.mode }}</span>
          <span>{{ formatPercent(item.confidence) }}</span>
          <span>{{ formatMs(item.elapsed_ms) }}</span>
          <span>{{ item.graph_path_count }} 路径 / {{ item.text_evidence_count }} 文档</span>
          <span>{{ formatTime(item.created_at) }}</span>
          <button class="link-button danger" type="button" @click="removeItem(item.id)">删除</button>
        </div>
      </div>

      <div class="pagination-row">
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <div>
          <button class="ghost-button small-button" :disabled="page <= 1" type="button" @click="goPage(page - 1)">上一页</button>
          <button class="ghost-button small-button" :disabled="page >= totalPages" type="button" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </section>
  </div>
</template>
