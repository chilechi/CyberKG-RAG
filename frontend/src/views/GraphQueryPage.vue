<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchGraphNeighbors } from "../api/graph";
import type { GraphData, GraphNode } from "../api/mock";
import GraphView from "../components/GraphView.vue";

const graph = ref<GraphData | null>(null);
const loading = ref(false);
const error = ref("");
const entityId = ref("CVE-2021-44228");
const depth = ref(4);

const selectedEntity = computed<GraphNode | null>(() => {
  if (!graph.value) return null;
  return graph.value.nodes.find((node) => node.id === entityId.value.trim()) ?? graph.value.nodes[0] ?? null;
});

const relatedEntities = computed(() => {
  if (!graph.value || !selectedEntity.value) return [];
  const selectedId = selectedEntity.value.id;
  const neighborIds = new Set<string>();
  graph.value.edges.forEach((edge) => {
    if (edge.source === selectedId) neighborIds.add(edge.target);
    if (edge.target === selectedId) neighborIds.add(edge.source);
  });
  return graph.value.nodes.filter((node) => neighborIds.has(node.id));
});

const nodeLegend = computed(() => {
  const countByType = new Map<string, number>();
  graph.value?.nodes.forEach((node) => {
    countByType.set(node.type, (countByType.get(node.type) ?? 0) + 1);
  });
  return Array.from(countByType, ([label, count]) => ({ label, count }));
});

const relationLegend = computed(() => {
  const countByType = new Map<string, number>();
  graph.value?.edges.forEach((edge) => {
    countByType.set(edge.relation, (countByType.get(edge.relation) ?? 0) + 1);
  });
  return Array.from(countByType, ([label, count]) => ({ label, count }));
});

async function loadGraph() {
  if (!entityId.value.trim()) {
    error.value = "请输入实体 ID";
    graph.value = null;
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    graph.value = await fetchGraphNeighbors(entityId.value.trim(), depth.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "图谱数据加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadGraph);
</script>

<template>
  <div class="page-grid graph-query-page">
    <section class="panel graph-search-panel">
      <div class="toolbar-row graph-toolbar">
        <label class="field wide">
          <span>实体名称 / CVE / CWE / CAPEC / ATT&CK 技术</span>
          <input v-model="entityId" type="text" placeholder="例如 CVE-2021-44228" @keyup.enter="loadGraph" />
        </label>
        <label class="field small">
          <span>查询深度</span>
          <select v-model.number="depth">
            <option :value="1">1 跳</option>
            <option :value="2">2 跳</option>
            <option :value="3">3 跳</option>
            <option :value="4">4 跳</option>
          </select>
        </label>
        <button class="primary small-button" :disabled="loading" type="button" @click="loadGraph">
          {{ loading ? "搜索中..." : "搜索" }}
        </button>
      </div>
    </section>

    <section class="graph-workbench tighter-grid">
      <div class="panel graph-visual-panel">
        <div class="section-heading compact">
          <div>
            <h2>图谱可视化</h2>
            <p>数据来自 Neo4j 邻居查询接口。</p>
          </div>
          <span class="panel-badge">真实接口</span>
        </div>
        <div v-if="loading" class="state-panel compact-state">正在加载图谱...</div>
        <div v-else-if="error" class="state-panel error compact-state">{{ error }}</div>
        <div v-else-if="!graph || graph.nodes.length === 0" class="state-panel compact-state">暂无图谱数据</div>
        <GraphView v-else :graph="graph" />
      </div>

      <aside class="panel entity-detail-panel">
        <div class="section-heading compact">
          <div>
            <h2>实体详情</h2>
            <p>默认展示当前查询实体或首个命中节点。</p>
          </div>
        </div>
        <div v-if="selectedEntity" class="entity-profile compact-profile">
          <span class="entity-avatar">{{ selectedEntity.type.slice(0, 1) }}</span>
          <div>
            <h3>{{ selectedEntity.name }}</h3>
            <small>{{ selectedEntity.id }} / {{ selectedEntity.type }}</small>
          </div>
          <p>{{ selectedEntity.description || "暂无描述" }}</p>
        </div>
        <dl class="compact-stats three-cols">
          <div>
            <dt>节点</dt>
            <dd>{{ graph?.nodes.length ?? "--" }}</dd>
          </div>
          <div>
            <dt>关系</dt>
            <dd>{{ graph?.edges.length ?? "--" }}</dd>
          </div>
          <div>
            <dt>邻居</dt>
            <dd>{{ relatedEntities.length || "--" }}</dd>
          </div>
        </dl>

        <div class="legend-block">
          <h3>节点图例</h3>
          <div v-if="nodeLegend.length > 0" class="legend-list">
            <span v-for="item in nodeLegend" :key="item.label">
              <i></i>{{ item.label }} <b>{{ item.count }}</b>
            </span>
          </div>
          <div v-else class="inline-empty">暂无节点图例</div>
        </div>

        <div class="legend-block">
          <h3>关系图例</h3>
          <div v-if="relationLegend.length > 0" class="legend-list relation-list">
            <span v-for="item in relationLegend" :key="item.label">
              <i></i>{{ item.label }} <b>{{ item.count }}</b>
            </span>
          </div>
          <div v-else class="inline-empty">暂无关系图例</div>
        </div>
      </aside>
    </section>

    <section class="panel path-panel">
      <div class="section-heading compact">
        <div>
          <h2>关联实体与多跳路径</h2>
          <p>根据本次 Neo4j 查询结果生成，不写静态路径。</p>
        </div>
      </div>
      <div v-if="graph && graph.edges.length > 0" class="edge-strip dense-strip">
        <span v-for="edge in graph.edges" :key="`${edge.source}-${edge.target}-${edge.relation}`">
          {{ edge.source }} → {{ edge.relation }} → {{ edge.target }}
        </span>
      </div>
      <div v-else class="empty-table compact-empty">暂无路径数据</div>
    </section>
  </div>
</template>
