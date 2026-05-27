<script setup lang="ts">
interface NavItem {
  key: string;
  label: string;
  icon: string;
}

defineProps<{
  activeKey: string;
  items: NavItem[];
}>();

defineEmits<{
  select: [key: string];
}>();
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">KG</div>
      <div>
        <strong>CyberKG-RAG</strong>
        <span>网络安全智能问答平台</span>
      </div>
    </div>

    <nav class="side-nav" aria-label="主导航">
      <button
        v-for="item in items"
        :key="item.key"
        :class="{ active: activeKey === item.key }"
        type="button"
        @click="$emit('select', item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-badge">
      <div class="shield">防</div>
      <p>知识图谱驱动</p>
      <span>PostgreSQL / Neo4j / Milvus</span>
    </div>
  </aside>
</template>
