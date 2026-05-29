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

const showNodeLabel = computed(() => props.graph.nodes.length <= 45);

function getSymbolSize(type: string) {
  if (type === "Vulnerability") return 54;
  if (type === "Tactic") return 34;
  if (type === "Technique") return 38;
  return 42;
}

function renderGraph() {
  if (!chartEl.value) return;
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }

  const categoryIndex = new Map(categories.value.map((item, index) => [item.name, index]));

  // ECharts 需要稳定的节点和边结构；大图默认隐藏边标签，避免关系文字遮挡。
  chart.setOption({
    animation: props.graph.nodes.length <= 60,
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
          symbolSize: getSymbolSize(node.type),
          category: categoryIndex.get(node.type) ?? 0,
        })),
        links: props.graph.edges.map((edge) => ({
          ...edge,
          label: {
            show: false,
            formatter: edge.relation,
          },
        })),
        force: {
          repulsion: 680,
          edgeLength: [120, 190],
          gravity: 0.08,
          layoutAnimation: props.graph.nodes.length <= 60,
        },
        label: {
          show: showNodeLabel.value,
          formatter: "{b}",
          fontSize: 11,
          color: "#1e293b",
        },
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: 7,
        lineStyle: {
          color: "#64748b",
          opacity: 0.45,
          curveness: 0.12,
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
