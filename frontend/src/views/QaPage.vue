<script setup lang="ts">
import { computed, ref } from "vue";

import { askQuestion, type QaMode } from "../api/qa";
import type { QaAnswer } from "../api/types";
import { renderMarkdown } from "../utils/markdown";

const question = ref("Log4Shell 可能关联哪些攻击技术？");
const selectedMode = ref<QaMode>("kg-rag");
const answer = ref<QaAnswer | null>(null);
const loading = ref(false);
const error = ref("");

const modeOptions: { key: QaMode; title: string; description: string }[] = [
  { key: "llm", title: "普通 LLM", description: "只调用 DeepSeek，不检索知识库" },
  { key: "rag", title: "普通 RAG", description: "检索 Milvus 文本证据后生成" },
  { key: "kg-rag", title: "KG-RAG", description: "结合 Neo4j 图谱路径和文本证据" },
];

const metrics = computed(() => [
  { label: "回答模式", value: answer.value ? answer.value.mode : "--" },
  { label: "置信度", value: answer.value ? `${Math.round(answer.value.confidence * 100)}%` : "--" },
  { label: "召回文档", value: answer.value ? answer.value.text_evidence.length.toString() : "--" },
  { label: "证据路径", value: answer.value ? answer.value.graph_paths.length.toString() : "--" },
]);

const renderedAnswer = computed(() => (answer.value ? renderMarkdown(answer.value.answer) : ""));

async function submitQuestion() {
  if (!question.value.trim()) {
    error.value = "请输入问题";
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    answer.value = await askQuestion(question.value.trim(), selectedMode.value);
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
          <p>选择一种问答模式后提交，页面只运行当前模式。</p>
        </div>
      </div>
      <textarea v-model="question" maxlength="2000" placeholder="例如：Log4Shell 漏洞的攻击原理和防护措施是什么？" />
      <div class="qa-mode-grid">
        <button
          v-for="mode in modeOptions"
          :key="mode.key"
          :class="['qa-mode-card', selectedMode === mode.key ? 'active' : '']"
          type="button"
          @click="selectedMode = mode.key"
        >
          <strong>{{ mode.title }}</strong>
          <span>{{ mode.description }}</span>
        </button>
      </div>
      <div class="question-actions">
        <span>{{ question.length }} / 2000</span>
        <button class="primary" :disabled="loading" type="button" @click="submitQuestion">
          {{ loading ? "生成中..." : "开始问答" }}
        </button>
      </div>
    </section>

    <section class="panel answer-panel">
      <div class="section-heading">
        <div>
          <h2>问答结果</h2>
          <p v-if="answer">{{ answer.mode }} · 问题：{{ answer.question }}</p>
        </div>
        <span v-if="answer" class="confidence">置信度 {{ Math.round(answer.confidence * 100) }}%</span>
      </div>
      <div v-if="error" class="state-panel error">{{ error }}</div>
      <div v-else-if="!answer && !loading" class="state-panel">提交问题后展示真实接口返回结果</div>
      <div v-else-if="loading" class="state-panel">正在生成答案...</div>
      <article v-else-if="answer" class="answer-content markdown-body" v-html="renderedAnswer"></article>
    </section>

    <aside class="qa-side">
      <section class="panel">
        <div class="section-heading compact">
          <div>
            <h2>问答指标</h2>
            <p>来自本次所选问答模式的返回结果。</p>
          </div>
        </div>
        <div class="qa-metric-grid">
          <div v-for="item in metrics" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>
    </aside>

    <section class="panel evidence-panel">
      <div class="section-heading compact">
        <div>
          <h2>图谱证据路径</h2>
          <p>KG-RAG 模式会返回 Neo4j 图谱路径；其他模式不使用图谱。</p>
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
          <p>普通 RAG 和 KG-RAG 会返回 Milvus 召回的文本片段。</p>
        </div>
      </div>
      <div v-if="answer && answer.text_evidence.length > 0" class="evidence-list">
        <div v-for="evidence in answer.text_evidence" :key="`${evidence.source}-${evidence.entity_id}`">
          <strong>{{ evidence.source }} / {{ evidence.entity_id }}</strong>
          <span>相似度 {{ Math.round(evidence.score * 100) }}%</span>
          <div class="markdown-body evidence-markdown" v-html="renderMarkdown(evidence.text)"></div>
        </div>
      </div>
      <div v-else class="empty-table">暂无文本证据</div>
    </section>
  </div>
</template>
