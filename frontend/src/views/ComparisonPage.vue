<script setup lang="ts">
import { computed, ref } from "vue";

import { runQaComparison, type QaComparisonResponse } from "../api/comparison";

const question = ref("Log4Shell 漏洞的攻击原理和防护措施是什么？");
const data = ref<QaComparisonResponse | null>(null);
const loading = ref(false);
const error = ref("");

const metricCards = computed(() => {
  if (!data.value) {
    return [
      { label: "最佳模式", value: "--", note: "等待实验" },
      { label: "最快模式", value: "--", note: "等待实验" },
      { label: "最高置信度", value: "--", note: "等待实验" },
      { label: "总耗时", value: "--", note: "等待实验" },
    ];
  }
  return [
    { label: "最佳模式", value: data.value.metrics.best_mode, note: "按置信度计算" },
    { label: "最快模式", value: data.value.metrics.fastest_mode, note: "按接口耗时计算" },
    { label: "最高置信度", value: `${Math.round(data.value.metrics.max_confidence * 100)}%`, note: "后端综合评分" },
    { label: "总耗时", value: `${data.value.metrics.total_elapsed_ms}ms`, note: "三种模式合计" },
  ];
});

async function submitComparison() {
  if (!question.value.trim()) {
    error.value = "请输入测试问题";
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    data.value = await runQaComparison(question.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : "问答对比实验失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="page-grid comparison-page">
    <section class="panel comparison-input-panel">
      <label class="field">
        <span>测试问题</span>
        <input v-model="question" type="text" placeholder="输入需要对比的问题" @keyup.enter="submitComparison" />
      </label>
      <button class="primary" :disabled="loading" type="button" @click="submitComparison">
        {{ loading ? "运行中..." : "运行对比" }}
      </button>
    </section>

    <section class="metric-grid history-metrics">
      <article v-for="item in metricCards" :key="item.label" class="metric-card compact-card">
        <span class="metric-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </section>

    <section v-if="error" class="panel state-panel error compact-state">{{ error }}</section>
    <section v-else-if="!data && !loading" class="panel state-panel compact-state">
      输入问题后运行普通 LLM、普通 RAG、KG-RAG 三种模式的实时对比
    </section>
    <section v-else-if="loading" class="panel state-panel compact-state">正在运行三种问答模式...</section>

    <section v-if="data" class="comparison-result-grid">
      <article v-for="result in data.results" :key="result.mode" class="panel comparison-card">
        <div class="section-heading compact">
          <div>
            <h2>{{ result.mode }}</h2>
            <p>置信度 {{ Math.round(result.confidence * 100) }}% · 耗时 {{ result.elapsed_ms }}ms</p>
          </div>
          <span :class="['mode-pill', result.mode === data.metrics.best_mode ? 'best' : '']">
            {{ result.mode === data.metrics.best_mode ? "最佳" : "对比" }}
          </span>
        </div>
        <p class="comparison-answer">{{ result.answer }}</p>
        <div class="comparison-score-grid">
          <div>
            <span>图谱路径</span>
            <strong>{{ result.graph_path_count }}</strong>
          </div>
          <div>
            <span>文本证据</span>
            <strong>{{ result.text_evidence_count }}</strong>
          </div>
        </div>
      </article>
    </section>

    <section v-if="data" class="panel">
      <div class="section-heading compact">
        <div>
          <h2>结果评估</h2>
          <p>由后端根据本次实时返回的置信度、耗时和证据数量生成。</p>
        </div>
      </div>
      <div class="comparison-table">
        <div class="comparison-row header">
          <span>模式</span>
          <span>置信度</span>
          <span>耗时</span>
          <span>图谱路径</span>
          <span>文本证据</span>
        </div>
        <div v-for="result in data.results" :key="`${result.mode}-row`" class="comparison-row">
          <strong>{{ result.mode }}</strong>
          <span>{{ Math.round(result.confidence * 100) }}%</span>
          <span>{{ result.elapsed_ms }}ms</span>
          <span>{{ result.graph_path_count }}</span>
          <span>{{ result.text_evidence_count }}</span>
        </div>
      </div>
    </section>

    <section v-if="data" class="panel evidence-panel">
      <div class="section-heading compact">
        <div>
          <h2>KG-RAG 证据</h2>
          <p>只展示完整 KG-RAG 模式返回的图谱路径和文本证据。</p>
        </div>
      </div>
      <template v-for="result in data.results" :key="`${result.mode}-evidence`">
        <div v-if="result.mode === 'KG-RAG'" class="comparison-evidence-layout">
          <div>
            <h3>图谱路径</h3>
            <div v-if="result.graph_paths.length > 0" class="path-chip-row dense-strip">
              <span v-for="(path, index) in result.graph_paths" :key="index">{{ path.join(" → ") }}</span>
            </div>
            <div v-else class="inline-empty">暂无图谱路径</div>
          </div>
          <div>
            <h3>文本证据</h3>
            <div v-if="result.text_evidence.length > 0" class="evidence-list">
              <div v-for="evidence in result.text_evidence" :key="`${evidence.source}-${evidence.entity_id}`">
                <strong>{{ evidence.source }} / {{ evidence.entity_id }}</strong>
                <span>相似度 {{ Math.round(evidence.score * 100) }}%</span>
                <p>{{ evidence.text }}</p>
              </div>
            </div>
            <div v-else class="inline-empty">暂无文本证据</div>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>
