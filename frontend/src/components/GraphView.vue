<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

import type { GraphData } from "../api/types";

const props = defineProps<{
  graph: GraphData;
}>();

const chartEl = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const categories = computed(() => {
  const types = Array.from(new Set(props.graph.nodes.map((node) => node.type)));
  return types.map((name) => ({ name }));
});

function renderGraph() {
  if (!chartEl.value) return;
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }

  const categoryIndex = new Map(categories.value.map((item, index) => [item.name, index]));

  // ECharts 需要稳定的节点和边结构；这里把后端返回字段映射成图谱组件字段。
  chart.setOption({
    tooltip: {
      trigger: "item",
      formatter: (params: any) => {
        if (params.dataType === "edge") {
          return `${params.data.source} → ${params.data.target}<br/>${params.data.relation}`;
        }
        return `${params.data.name}<br/>${params.data.type}<br/>${params.data.description ?? ""}`;
      },
    },
    legend: [
      {
        data: categories.value.map((item) => item.name),
        bottom: 0,
      },
    ],
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        categories: categories.value,
        data: props.graph.nodes.map((node) => ({
          ...node,
          symbolSize: node.type === "Vulnerability" ? 62 : 48,
          category: categoryIndex.get(node.type) ?? 0,
        })),
        links: props.graph.edges.map((edge) => ({
          ...edge,
          label: {
            show: true,
            formatter: edge.relation,
          },
        })),
        force: {
          repulsion: 420,
          edgeLength: 155,
        },
        label: {
          show: true,
          formatter: "{b}",
        },
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: 8,
        lineStyle: {
          color: "#64748b",
          curveness: 0.08,
        },
        emphasis: {
          focus: "adjacency",
        },
      },
    ],
  });
}

function handleResize() {
  chart?.resize();
}

onMounted(() => {
  renderGraph();
  window.addEventListener("resize", handleResize);
});

watch(
  () => props.graph,
  () => renderGraph(),
  { deep: true },
);

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="chartEl" class="graph-canvas" />
</template>
