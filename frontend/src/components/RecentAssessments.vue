<script setup lang="ts">
type Assessment = {
  name: string;
  position: string;
  score: number;
  status: "completed" | "pending";
  date: string;
};

defineProps<{
  items: Assessment[];
}>();
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">最近测评</h3>
      <button class="btn-secondary">查看全部</button>
    </div>
    <div class="card-body list-body">
      <div v-for="item in items" :key="item.name" class="list-row">
        <div>
          <div class="row-title">{{ item.name }}</div>
          <div class="row-sub">{{ item.position }}</div>
        </div>
        <div class="row-meta">
          <span class="score">{{ item.score }}分</span>
          <span class="status" :data-status="item.status">
            <i :class="item.status === 'completed' ? 'ri-checkbox-circle-line' : 'ri-time-line'"></i>
            {{ item.status === "completed" ? "完成" : "待完成" }}
          </span>
          <span class="date">{{ item.date }}</span>
        </div>
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
}

.btn-secondary {
  border: 1px solid var(--border-default);
  background: var(--bg-subtle);
  color: var(--text-primary);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  cursor: pointer;
}

.card-body.list-body {
  padding: 0;
}

.list-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.list-row:last-child {
  border-bottom: none;
}

.row-title {
  font-weight: 600;
}

.row-sub {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.row-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.score {
  font-weight: 700;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-tertiary);
}

.status[data-status="completed"] {
  color: var(--accent-success);
}

.date {
  color: var(--text-tertiary);
}
</style>
