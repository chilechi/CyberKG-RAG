<script setup lang="ts">
import { ref } from "vue";

import MockGraphPage from "./views/MockGraphPage.vue";
import MockQaPage from "./views/MockQaPage.vue";

type PageKey = "graph" | "qa";

const activePage = ref<PageKey>("graph");
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>CyberKG-RAG</h1>
        <p>网络安全知识图谱问答系统 mock 演示</p>
      </div>
      <nav class="tabs" aria-label="功能导航">
        <button :class="{ active: activePage === 'graph' }" @click="activePage = 'graph'">
          图谱
        </button>
        <button :class="{ active: activePage === 'qa' }" @click="activePage = 'qa'">
          问答
        </button>
      </nav>
    </header>

    <MockGraphPage v-if="activePage === 'graph'" />
    <MockQaPage v-else />
  </main>
</template>
