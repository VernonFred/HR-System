<script setup lang="ts">
import { computed } from "vue";
import EChartContainer from "../EChartContainer.vue";
import type { PersonalityDimension } from "../../types/candidate";

const props = defineProps<{
  dimensions: PersonalityDimension[];
}>();

const option = computed(() => {
  const dims = props.dimensions || [];
  return {
    tooltip: {},
    backgroundColor: "transparent",
    radar: {
      indicator: dims.map((d) => ({ name: d.label, max: 100 })),
      radius: 85,
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.15)" } },
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.15)" } },
      splitArea: { areaStyle: { color: ["rgba(106,90,236,0.06)", "rgba(106,90,236,0.03)"] } },
      name: { color: "#4A4E55", fontSize: 12 },
    },
    series: [
      {
        type: "radar",
        areaStyle: { opacity: 1, color: "rgba(106, 90, 236, 0.20)" },
        lineStyle: { color: "#6A5AEC", width: 2 },
        symbol: "circle",
        itemStyle: { color: "#6A5AEC" },
        data: [{ value: dims.map((d) => d.score), name: "人格画像" }],
      },
    ],
  };
});
</script>

<template>
  <div class="chart-card">
    <div class="card-header">
      <h4>人格维度雷达</h4>
    </div>
    <div class="card-body">
      <EChartContainer :option="option" />
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-weight: 600;
  font-size: 18px;
  color: #1b1c1f;
}
.card-body {
  padding: 16px;
}
</style>
