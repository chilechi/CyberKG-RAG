<script setup lang="ts">
import { computed, ref } from "vue";

import AppSidebar from "./components/AppSidebar.vue";
import AppTopbar from "./components/AppTopbar.vue";
import DashboardPage from "./views/DashboardPage.vue";
import DataManagementPage from "./views/DataManagementPage.vue";
import GraphQueryPage from "./views/GraphQueryPage.vue";
import HistoryPage from "./views/HistoryPage.vue";
import QaPage from "./views/QaPage.vue";
import ReservedPage from "./views/ReservedPage.vue";

type PageKey =
  | "dashboard"
  | "graph"
  | "qa"
  | "comparison"
  | "completion"
  | "data"
  | "history"
  | "settings";

interface NavItem {
  key: PageKey;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", label: "系统总览", icon: "⌂" },
  { key: "graph", label: "知识图谱查询", icon: "◎" },
  { key: "qa", label: "智能问答", icon: "▣" },
  { key: "comparison", label: "问答对比实验", icon: "≋" },
  { key: "completion", label: "知识补全实验", icon: "✣" },
  { key: "data", label: "数据管理", icon: "◫" },
  { key: "history", label: "问答历史", icon: "◷" },
  { key: "settings", label: "系统设置", icon: "⚙" },
];

const activePage = ref<PageKey>("dashboard");

function selectPage(key: string) {
  activePage.value = key as PageKey;
}

const pageMeta = computed(() => {
  const meta: Record<PageKey, { title: string; subtitle: string }> = {
    dashboard: { title: "系统总览", subtitle: "查看三库状态、真实样例数据规模与 KG-RAG 链路" },
    graph: { title: "知识图谱查询", subtitle: "基于 Neo4j 查询实体邻居和证据路径" },
    qa: { title: "智能问答", subtitle: "融合图谱路径与 Milvus 文本证据生成答案" },
    comparison: { title: "问答对比实验", subtitle: "对比不同问答模式的回答效果与质量表现" },
    completion: { title: "知识补全实验", subtitle: "预留 PyKEEN 知识补全训练和评估结果展示" },
    data: { title: "数据管理", subtitle: "统一管理数据源、文档与向量数据，保障知识库质量与一致性" },
    history: { title: "问答历史", subtitle: "查看和管理历史问答记录" },
    settings: { title: "系统设置", subtitle: "查看公开系统配置，敏感密钥不会展示" },
  };
  return meta[activePage.value];
});
</script>

<template>
  <div class="app-shell">
    <AppSidebar :items="navItems" :active-key="activePage" @select="selectPage" />
    <main class="workspace">
      <AppTopbar :title="pageMeta.title" :subtitle="pageMeta.subtitle" />
      <DashboardPage v-if="activePage === 'dashboard'" />
      <GraphQueryPage v-else-if="activePage === 'graph'" />
      <QaPage v-else-if="activePage === 'qa'" />
      <ReservedPage
        v-else-if="activePage === 'comparison'"
        title="问答对比实验"
        description="普通 LLM、普通 RAG、KG-RAG 的对比评测接口已预留。"
        endpoint="/api/experiments/qa-comparison"
      />
      <ReservedPage
        v-else-if="activePage === 'completion'"
        title="知识补全实验"
        description="TransE、ComplEx、RotatE 等模型训练结果展示位已预留。"
        endpoint="/api/experiments/kg-completion"
      />
      <DataManagementPage v-else-if="activePage === 'data'" />
      <HistoryPage v-else-if="activePage === 'history'" />
      <ReservedPage
        v-else
        title="系统设置"
        description="当前只展示可公开配置，API Key 等敏感信息不会返回前端。"
        endpoint="/api/settings"
        settings
      />
    </main>
  </div>
</template>
