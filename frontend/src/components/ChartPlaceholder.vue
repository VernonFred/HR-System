<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">{{ title }}</h3>
    </div>
    <div class="card-body">
      <div class="chart-placeholder">
        <div class="chart-grid"></div>
        <p>即将接入 ECharts 与后端数据</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
}

.card-body {
  padding: var(--space-4);
}

.chart-placeholder {
  min-height: 200px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  color: var(--text-tertiary);
  gap: var(--space-2);
  text-align: center;
}

.chart-grid {
  width: 120px;
  height: 80px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(59, 130, 246, 0.1));
  border-radius: var(--radius-md);
}
</style>
