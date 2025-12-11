<script setup lang="ts">
type StatCard = {
  title: string;
  value: string;
  change?: string;
  icon?: string;
  accent?: "primary" | "success" | "warning" | "danger" | "info";
};

defineProps<{
  items: StatCard[];
}>();

const accentColor = (accent?: StatCard["accent"]) => {
  switch (accent) {
    case "success":
      return "var(--accent-success)";
    case "warning":
      return "var(--accent-warning)";
    case "danger":
      return "var(--accent-danger)";
    case "info":
      return "var(--accent-info)";
    default:
      return "var(--accent-primary)";
  }
};
</script>

<template>
  <div class="stats-grid">
    <div v-for="item in items" :key="item.title" class="stat-card">
      <div class="stat-icon" :style="{ color: accentColor(item.accent) }">
        <i :class="item.icon || 'ri-bar-chart-line'"></i>
      </div>
      <div class="stat-meta">
        <div class="stat-title">{{ item.title }}</div>
        <div class="stat-value">{{ item.value }}</div>
        <div v-if="item.change" class="stat-change">{{ item.change }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.stat-card {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  display: grid;
  place-items: center;
  font-size: 20px;
}

.stat-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-title {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: 700;
}

.stat-change {
  color: var(--accent-success);
  font-size: var(--text-sm);
}
</style>
