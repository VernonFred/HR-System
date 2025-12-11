<script setup lang="ts">
import HeaderBar from "../components/HeaderBar.vue";
import StatCards from "../components/StatCards.vue";
import ChartPlaceholder from "../components/ChartPlaceholder.vue";
import RecentAssessments from "../components/RecentAssessments.vue";

const stats = [
  { title: "候选人总数", value: "128", change: "+12 本周", icon: "ri-user-3-line" },
  { title: "进行中测评", value: "24", change: "8 待提醒", icon: "ri-psychotherapy-line", accent: "info" },
  { title: "平均匹配度", value: "78%", change: "+3%", icon: "ri-line-chart-line", accent: "success" },
  { title: "高优先级", value: "12", change: "3 新增", icon: "ri-alert-line", accent: "warning" },
];

const recent = [
  { name: "张三", position: "产品经理", score: 85, status: "completed", date: "12-02" },       // EPQ测评
  { name: "李四", position: "实施工程师", score: 75, status: "completed", date: "12-03" },   // DISC测评
  { name: "王五", position: "软件工程师", score: 80, status: "completed", date: "12-04" },   // MBTI测评
];
</script>

<template>
  <div class="dashboard">
    <HeaderBar title="数据概览" subtitle="保持与旧版一致的指标与图表，将逐步接入后端数据" />
    <StatCards :items="stats" />

    <div class="charts-grid">
      <ChartPlaceholder title="岗位分布" />
      <ChartPlaceholder title="匹配度分布" />
    </div>

    <div class="charts-grid">
      <ChartPlaceholder title="EPQ 维度均值对比" />
      <ChartPlaceholder title="测评趋势" />
    </div>

    <RecentAssessments :items="recent" />
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-3);
}
</style>
