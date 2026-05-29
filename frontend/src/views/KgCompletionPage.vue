<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  fetchKgCompletionSummary,
  predictKgCompletion,
  type KgCompletionPredictResponse,
  type KgCompletionResponse,
} from "../api/kgCompletion";

const summary = ref<KgCompletionResponse | null>(null);
const prediction = ref<KgCompletionPredictResponse | null>(null);
const loading = ref(false);
const predicting = ref(false);
const error = ref("");
const predictError = ref("");

const head = ref("CVE-2021-44228");
const relation = ref("HAS_WEAKNESS");
const topK = ref(3);

const metricCards = computed(() => {
  if (!summary.value) {
    return [
      { label: "实体数量", value: "--", note: "等待加载" },
      { label: "关系类型", value: "--", note: "等待加载" },
      { label: "三元组", value: "--", note: "等待加载" },
      { label: "训练/验证/测试", value: "--", note: "等待加载" },
    ];
  }
  const dataset = summary.value.dataset;
  return [
    { label: "实体数量", value: dataset.entity_count.toString(), note: "PostgreSQL entities" },
    { label: "关系类型", value: dataset.relation_count.toString(), note: "relations.relation" },
    { label: "三元组", value: dataset.triple_count.toString(), note: "PostgreSQL relations" },
    {
      label: "训练/验证/测试",
      value: `${dataset.train_count}/${dataset.valid_count}/${dataset.test_count}`,
      note: "按 8:1:1 划分",
    },
  ];
});

const bestModel = computed(() => {
  if (!summary.value || summary.value.model_metrics.length === 0) return "";
  return [...summary.value.model_metrics].sort((left, right) => right.mrr - left.mrr)[0].model;
});

async function loadSummary() {
  loading.value = true;
  error.value = "";
  try {
    summary.value = await fetchKgCompletionSummary();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "知识补全实验加载失败";
  } finally {
    loading.value = false;
  }
}

async function submitPrediction() {
  if (!head.value.trim() || !relation.value.trim()) {
    predictError.value = "请输入头实体和关系类型";
    return;
  }
  predicting.value = true;
  predictError.value = "";
  try {
    prediction.value = await predictKgCompletion(head.value.trim(), relation.value.trim(), topK.value);
  } catch (err) {
    predictError.value = err instanceof Error ? err.message : "Top-K 补全预测失败";
  } finally {
    predicting.value = false;
  }
}

onMounted(async () => {
  await loadSummary();
  await submitPrediction();
});
</script>

<template>
  <div class="page-grid kg-completion-page">
    <section v-if="loading" class="panel state-panel compact-state">正在加载知识补全实验...</section>
    <section v-else-if="error" class="panel state-panel error compact-state">{{ error }}</section>

    <template v-if="summary">
      <section class="metric-grid history-metrics">
        <article v-for="item in metricCards" :key="item.label" class="metric-card compact-card">
          <span class="metric-label">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </section>

      <section class="kg-completion-main">
        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>模型性能对比</h2>
              <p>基于 PostgreSQL 三元组按 8:1:1 划分，在测试三元组上计算 MRR 和 Hits 指标。</p>
            </div>
          </div>
          <div class="kg-model-table">
            <div class="kg-model-row header">
              <span>模型</span>
              <span>MRR</span>
              <span>Hits@1</span>
              <span>Hits@3</span>
              <span>Hits@10</span>
              <span>评测耗时</span>
            </div>
            <div v-for="item in summary.model_metrics" :key="item.model" class="kg-model-row">
              <strong>{{ item.model }}</strong>
              <span>{{ item.mrr.toFixed(2) }}</span>
              <span>{{ item.hits_at_1.toFixed(2) }}</span>
              <span>{{ item.hits_at_3.toFixed(2) }}</span>
              <span>{{ item.hits_at_10.toFixed(2) }}</span>
              <span>{{ item.train_seconds }}s</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>Top-K 补全预测</h2>
              <p>预测尾实体：Head + Relation → Tail。</p>
            </div>
          </div>
          <div class="kg-predict-form">
            <label class="field">
              <span>Head</span>
              <input v-model="head" type="text" placeholder="CVE-2021-44228" />
            </label>
            <label class="field">
              <span>Relation</span>
              <input v-model="relation" type="text" placeholder="HAS_WEAKNESS" />
            </label>
            <label class="field">
              <span>Top K</span>
              <select v-model.number="topK">
                <option :value="3">3</option>
                <option :value="5">5</option>
                <option :value="10">10</option>
              </select>
            </label>
            <button class="primary" :disabled="predicting" type="button" @click="submitPrediction">
              {{ predicting ? "预测中..." : "查询" }}
            </button>
          </div>
          <div v-if="predictError" class="state-panel error compact-state">{{ predictError }}</div>
          <div v-else-if="prediction" class="kg-prediction-list">
            <div v-for="item in prediction.predictions" :key="item.tail" class="kg-prediction-row">
              <span class="rank-badge">{{ item.rank }}</span>
              <div>
                <strong>{{ item.tail }} / {{ item.tail_name }}</strong>
                <small>{{ item.tail_type }} · {{ item.reason }}</small>
              </div>
              <b>{{ Math.round(item.score * 100) }}%</b>
            </div>
          </div>
          <div v-else class="empty-table compact-empty">暂无预测结果</div>
        </div>
      </section>

      <section class="kg-completion-main">
        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>训练曲线</h2>
              <p>展示 MRR、Hits@10 和 Loss 的轮次变化。</p>
            </div>
          </div>
          <div class="curve-grid">
            <div>
              <h3>MRR</h3>
              <div v-for="point in summary.mrr_curve" :key="`mrr-${point.epoch}`" class="curve-row">
                <span>{{ point.epoch }}</span>
                <b :style="{ width: `${point.rotate * 100}%` }"></b>
                <small>{{ point.rotate.toFixed(2) }}</small>
              </div>
            </div>
            <div>
              <h3>Hits@10</h3>
              <div v-for="point in summary.hits_at_10_curve" :key="`hits-${point.epoch}`" class="curve-row">
                <span>{{ point.epoch }}</span>
                <b :style="{ width: `${point.rotate * 100}%` }"></b>
                <small>{{ point.rotate.toFixed(2) }}</small>
              </div>
            </div>
            <div>
              <h3>Loss</h3>
              <div v-for="point in summary.loss_curve" :key="`loss-${point.epoch}`" class="curve-row loss">
                <span>{{ point.epoch }}</span>
                <b :style="{ width: `${point.rotate * 100}%` }"></b>
                <small>{{ point.rotate.toFixed(2) }}</small>
              </div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="section-heading compact">
            <div>
              <h2>实验结论</h2>
              <p>最佳模型：{{ bestModel }}</p>
            </div>
          </div>
          <p class="kg-conclusion">{{ summary.conclusion }}</p>
          <div class="legend-block">
            <h3>关系类型分布</h3>
            <div class="legend-list relation-list">
              <span v-for="(count, name) in summary.dataset.relation_types" :key="name">
                <i></i>{{ name }}<b>{{ count }}</b>
              </span>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
