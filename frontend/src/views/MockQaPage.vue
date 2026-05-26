<script setup lang="ts">
import { ref } from "vue";

import { askMockQuestion, type QaAnswer } from "../api/mock";

const question = ref("Log4Shell 可能关联哪些攻击技术？");
const answer = ref<QaAnswer | null>(null);
const loading = ref(false);
const error = ref("");

async function submitQuestion() {
  if (!question.value.trim()) {
    error.value = "请输入问题";
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    answer.value = await askMockQuestion(question.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : "问答请求失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="panel qa-panel">
    <div class="section-heading">
      <div>
        <h2>KG-RAG 问答</h2>
        <p>先用 mock 数据固定答案、路径证据和文本证据的展示方式</p>
      </div>
    </div>

    <div class="question-row">
      <input v-model="question" type="text" placeholder="输入网络安全问题" @keyup.enter="submitQuestion" />
      <button class="primary" :disabled="loading" @click="submitQuestion">
        {{ loading ? "生成中..." : "提问" }}
      </button>
    </div>

    <div v-if="error" class="state error">{{ error }}</div>
    <div v-if="!answer && !loading" class="state">输入问题后查看 mock 回答</div>

    <article v-if="answer" class="answer-card">
      <div class="answer-header">
        <h3>回答</h3>
        <span>置信度 {{ Math.round(answer.confidence * 100) }}%</span>
      </div>
      <p>{{ answer.answer }}</p>

      <h4>图谱路径证据</h4>
      <ul>
        <li v-for="(path, index) in answer.graph_paths" :key="index">
          {{ path.join(" → ") }}
        </li>
      </ul>

      <h4>文本证据</h4>
      <div class="evidence-list">
        <div v-for="evidence in answer.text_evidence" :key="`${evidence.source}-${evidence.entity_id}`">
          <strong>{{ evidence.source }} / {{ evidence.entity_id }}</strong>
          <span>相似度 {{ Math.round(evidence.score * 100) }}%</span>
          <p>{{ evidence.text }}</p>
        </div>
      </div>
    </article>
  </section>
</template>
