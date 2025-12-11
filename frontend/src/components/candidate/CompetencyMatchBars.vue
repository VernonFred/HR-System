<script setup lang="ts">
import type { CompetencyScore } from "../../types/candidate";

const props = defineProps<{
  competencies: CompetencyScore[];
}>();
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h4>岗位胜任力匹配</h4>
    </div>
    <div class="card-body">
      <div v-for="item in props.competencies" :key="item.key" class="bar-row">
        <div class="bar-label">
          <span>{{ item.label }}</span>
          <span class="score">{{ item.score }}%</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: item.score + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-weight: 600;
  font-size: 18px;
  color: #1b1c1f;
}
.card-body {
  padding: 20px;
  display: grid;
  gap: 16px;
}
.bar-row {
  display: grid;
  gap: 6px;
}
.bar-label {
  display: flex;
  justify-content: space-between;
  color: #4a4e55;
  font-size: 14px;
}
.score {
  color: #1b1c1f;
  font-weight: 700;
}
.bar-track {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(135deg, #6a5aec, #a798ff);
}
</style>
