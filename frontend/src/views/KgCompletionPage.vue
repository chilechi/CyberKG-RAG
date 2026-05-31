<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  fetchKgCompletionSummary,
  predictKgCompletion,
  type KgCompletionModelMetric,
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

function modelKey(model: string) {
  return model.toLowerCase() as "transe" | "complex" | "rotate";
}

function scoreModel(item: KgCompletionModelMetric) {
  return item.mrr * 0.45 + item.hits_at_1 * 0.15 + item.hits_at_3 * 0.15 + item.hits_at_10 * 0.25;
}

const enrichedModelMetrics = computed(() => {
  if (!summary.value) return [];
  const maxScore = Math.max(...summary.value.model_metrics.map(scoreModel), 0.01);
  const maxTrainSeconds = Math.max(...summary.value.model_metrics.map((item) => item.train_seconds), 1);
  return summary.value.model_metrics
    .map((item) => ({
      ...item,
      score: scoreModel(item),
      scoreRate: scoreModel(item) / maxScore,
      trainRate: item.train_seconds / maxTrainSeconds,
    }))
    .sort((left, right) => right.score - left.score)
    .map((item, index) => ({ ...item, rank: index + 1 }));
});

const bestMetric = computed(() => enrichedModelMetrics.value[0]);

function sampleCurve<T>(items: T[], maxPoints = 10) {
  if (items.length <= maxPoints) {
    return items;
  }
  const step = (items.length - 1) / (maxPoints - 1);
  return Array.from({ length: maxPoints }, (_, index) => items[Math.round(index * step)]);
}

const sampledLossCurve = computed(() => sampleCurve(summary.value?.loss_curve ?? [], 8));

const analysisCards = computed(() => {
  if (!summary.value || !bestMetric.value) return [];
  const dataset = summary.value.dataset;
  const bestKey = modelKey(bestMetric.value.model);
  const firstLoss = summary.value.loss_curve[0]?.[bestKey] ?? 0;
  const lastLoss = summary.value.loss_curve[summary.value.loss_curve.length - 1]?.[bestKey] ?? 0;
  const lossDrop = firstLoss > 0 ? ((firstLoss - lastLoss) / firstLoss) * 100 : 0;
  const avgTrainSeconds =
    summary.value.model_metrics.reduce((total, item) => total + item.train_seconds, 0) /
    Math.max(summary.value.model_metrics.length, 1);

  return [
    { label: "最佳模型", value: bestMetric.value.model, note: `综合分 ${bestMetric.value.score.toFixed(3)}` },
    { label: "测试规模", value: dataset.test_count.toString(), note: `占全量 ${((dataset.test_count / dataset.triple_count) * 100).toFixed(1)}%` },
    { label: "Loss 下降", value: `${Math.max(lossDrop, 0).toFixed(0)}%`, note: `${firstLoss.toFixed(2)} → ${lastLoss.toFixed(2)}` },
    { label: "平均训练耗时", value: `${avgTrainSeconds.toFixed(0)}s`, note: `${summary.value.model_metrics.length} 个模型对比` },
  ];
});

const entityTypeRows = computed(() => {
  if (!summary.value) return [];
  return Object.entries(summary.value.dataset.entity_types).sort((left, right) => right[1] - left[1]);
});

const relationTypeRows = computed(() => {
  if (!summary.value) return [];
  return Object.entries(summary.value.dataset.relation_types).sort((left, right) => right[1] - left[1]);
});

const maxEntityTypeCount = computed(() => Math.max(...entityTypeRows.value.map(([, count]) => count), 1));
const maxRelationTypeCount = computed(() => Math.max(...relationTypeRows.value.map(([, count]) => count), 1));

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
              <span>综合分</span>
              <span>MRR</span>
              <span>Hits@10</span>
              <span>训练耗时</span>
              <span>排名</span>
            </div>
            <div v-for="item in enrichedModelMetrics" :key="item.model" class="kg-model-row">
              <strong>{{ item.model }}</strong>
              <span class="metric-bar-cell">
                <b :style="{ width: `${item.scoreRate * 100}%` }"></b>
                <small>{{ item.score.toFixed(3) }}</small>
              </span>
              <span>{{ item.mrr.toFixed(2) }}</span>
              <span>{{ item.hits_at_10.toFixed(2) }}</span>
              <span class="metric-bar-cell neutral">
                <b :style="{ width: `${item.trainRate * 100}%` }"></b>
                <small>{{ item.train_seconds }}s</small>
              </span>
              <span class="rank-text">#{{ item.rank }}</span>
            </div>
          </div>
          <div class="model-detail-grid">
            <article v-for="item in enrichedModelMetrics" :key="`detail-${item.model}`" class="model-detail-card">
              <div>
                <strong>{{ item.model }}</strong>
                <small>MRR {{ item.mrr.toFixed(3) }} · Hits@1 {{ item.hits_at_1.toFixed(3) }}</small>
              </div>
              <div class="mini-metric-list">
                <span><i :style="{ width: `${item.hits_at_3 * 100}%` }"></i>Hits@3 {{ item.hits_at_3.toFixed(2) }}</span>
                <span><i :style="{ width: `${item.hits_at_10 * 100}%` }"></i>Hits@10 {{ item.hits_at_10.toFixed(2) }}</span>
              </div>
            </article>
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
              <h2>训练与评测指标</h2>
              <p>基于当前训练结果展示模型排名、数据切分、类型分布和抽样后的 Loss 下降趋势。</p>
            </div>
          </div>
          <div class="experiment-card-grid">
            <article v-for="item in analysisCards" :key="item.label" class="experiment-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.note }}</small>
            </article>
          </div>
          <div class="curve-grid">
            <div>
              <h3>MRR 对比</h3>
              <div v-for="item in enrichedModelMetrics" :key="`mrr-${item.model}`" class="curve-row">
                <span>{{ item.model }}</span>
                <b :style="{ width: `${item.mrr * 100}%` }"></b>
                <small>{{ item.mrr.toFixed(2) }}</small>
              </div>
            </div>
            <div>
              <h3>Hits@10 对比</h3>
              <div v-for="item in enrichedModelMetrics" :key="`hits-${item.model}`" class="curve-row">
                <span>{{ item.model }}</span>
                <b :style="{ width: `${item.hits_at_10 * 100}%` }"></b>
                <small>{{ item.hits_at_10.toFixed(2) }}</small>
              </div>
            </div>
            <div>
              <h3>Loss 趋势</h3>
              <div v-for="point in sampledLossCurve" :key="`loss-${point.epoch}`" class="curve-row loss">
                <span>{{ point.epoch }}</span>
                <b :style="{ width: `${point.rotate * 100}%` }"></b>
                <small>{{ point.rotate.toFixed(2) }}</small>
              </div>
            </div>
          </div>
          <div class="distribution-grid">
            <div>
              <h3>实体类型分布</h3>
              <div v-for="[name, count] in entityTypeRows" :key="`entity-${name}`" class="distribution-row">
                <span>{{ name }}</span>
                <b><i :style="{ width: `${(count / maxEntityTypeCount) * 100}%` }"></i></b>
                <small>{{ count }}</small>
              </div>
            </div>
            <div>
              <h3>关系类型分布</h3>
              <div v-for="[name, count] in relationTypeRows" :key="`relation-${name}`" class="distribution-row relation">
                <span>{{ name }}</span>
                <b><i :style="{ width: `${(count / maxRelationTypeCount) * 100}%` }"></i></b>
                <small>{{ count }}</small>
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
