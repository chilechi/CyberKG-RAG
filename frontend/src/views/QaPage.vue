<script setup lang="ts">
import { computed, ref } from "vue";

import { askKgRagQuestion } from "../api/qa";
import type { QaAnswer } from "../api/mock";

const question = ref("Log4Shell 可能关联哪些攻击技术？");
const answer = ref<QaAnswer | null>(null);
const loading = ref(false);
const error = ref("");

const metrics = computed(() => [
  { label: "置信度", value: answer.value ? `${Math.round(answer.value.confidence * 100)}%` : "--" },
  { label: "召回文档", value: answer.value ? answer.value.text_evidence.length.toString() : "--" },
  { label: "证据路径", value: answer.value ? answer.value.graph_paths.length.toString() : "--" },
  { label: "命中三元组", value: answer.value ? answer.value.graph_paths.flat().length.toString() : "--" },
]);

async function submitQuestion() {
  if (!question.value.trim()) {
    error.value = "请输入问题";
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    answer.value = await askKgRagQuestion(question.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : "问答请求失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="qa-prototype-layout">
    <section class="panel question-panel">
      <div class="section-heading">
        <div>
          <h2>请输入您的问题</h2>
          <p>当前已接入 KG-RAG 真实接口。</p>
        </div>
      </div>
      <textarea v-model="question" maxlength="2000" placeholder="例如：Log4Shell 漏洞的攻击原理和防护措施是什么？" />
      <div class="question-actions">
        <span>{{ question.length }} / 2000</span>
        <button class="primary" :disabled="loading" type="button" @click="submitQuestion">
          {{ loading ? "生成中..." : "开始问答" }}
        </button>
      </div>
    </section>

    <section class="panel mode-panel">
      <div class="section-heading compact">
        <div>
          <h2>选择问答模式</h2>
          <p>未完成模式只显示预留状态。</p>
        </div>
      </div>
      <div class="mode-grid">
        <div class="mode-card reserved">
          <strong>普通 LLM</strong>
          <span>接口预留</span>
        </div>
        <div class="mode-card reserved">
          <strong>普通 RAG</strong>
          <span>接口预留</span>
        </div>
        <div class="mode-card active">
          <strong>KG-RAG</strong>
          <span>图谱路径 + 文本证据</span>
        </div>
      </div>
    </section>

    <section class="panel answer-panel">
      <div class="section-heading">
        <div>
          <h2>问答结果</h2>
          <p v-if="answer">问题：{{ answer.question }}</p>
        </div>
        <span v-if="answer" class="confidence">置信度 {{ Math.round(answer.confidence * 100) }}%</span>
      </div>
      <div v-if="error" class="state-panel error">{{ error }}</div>
      <div v-else-if="!answer && !loading" class="state-panel">提交问题后展示真实接口返回结果</div>
      <div v-else-if="loading" class="state-panel">正在生成答案...</div>
      <article v-else-if="answer" class="answer-content">
        <p>{{ answer.answer }}</p>
        <div class="answer-actions">
          <button class="ghost-button" type="button">有用（预留）</button>
          <button class="ghost-button" type="button">没用（预留）</button>
          <button class="ghost-button" type="button">复制（预留）</button>
        </div>
      </article>
    </section>

    <aside class="qa-side">
      <section class="panel">
        <div class="section-heading compact">
          <div>
            <h2>问答指标</h2>
            <p>来自本次 KG-RAG 返回结果。</p>
          </div>
        </div>
        <div class="qa-metric-grid">
          <div v-for="item in metrics" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-heading compact">
          <div>
            <h2>相关问题推荐</h2>
            <p>推荐算法未实现，当前仅展示预留状态。</p>
          </div>
        </div>
        <div class="empty-table">推荐问题接口预留，暂无真实推荐数据</div>
      </section>
    </aside>

    <section class="panel evidence-panel">
      <div class="section-heading compact">
        <div>
          <h2>图谱证据路径</h2>
          <p>展示后端返回的真实路径证据。</p>
        </div>
      </div>
      <div v-if="answer && answer.graph_paths.length > 0" class="path-chip-row">
        <span v-for="(path, index) in answer.graph_paths" :key="index">
          {{ path.join(" → ") }}
        </span>
      </div>
      <div v-else class="empty-table">暂无路径证据</div>
    </section>

    <section class="panel evidence-panel">
      <div class="section-heading compact">
        <div>
          <h2>文本证据片段</h2>
          <p>展示 Milvus 召回的真实文本片段。</p>
        </div>
      </div>
      <div v-if="answer && answer.text_evidence.length > 0" class="evidence-list">
        <div v-for="evidence in answer.text_evidence" :key="`${evidence.source}-${evidence.entity_id}`">
          <strong>{{ evidence.source }} / {{ evidence.entity_id }}</strong>
          <span>相似度 {{ Math.round(evidence.score * 100) }}%</span>
          <p>{{ evidence.text }}</p>
        </div>
      </div>
      <div v-else class="empty-table">暂无文本证据</div>
    </section>
  </div>
</template>
