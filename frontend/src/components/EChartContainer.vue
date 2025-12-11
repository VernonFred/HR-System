<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import { init, use, type ECharts, type EChartsOption, type SetOptionOpts } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
} from "echarts/components";
import { BarChart, LineChart, PieChart, RadarChart } from "echarts/charts";

// Register only used components to reduce bundle size.
use([
  CanvasRenderer,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
]);

type Theme = "dark" | "light";

const props = defineProps<{
  option: EChartsOption;
  theme?: Theme;
  setOptionOpts?: SetOptionOpts;
}>();

const chartRef = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;

const renderChart = () => {
  if (!chartRef.value) return;
  if (!instance) {
    instance = init(chartRef.value, props.theme || "dark");
  }
  instance.setOption(props.option, props.setOptionOpts);
};

const resizeHandler = () => {
  instance?.resize();
};

onMounted(() => {
  renderChart();
  window.addEventListener("resize", resizeHandler);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeHandler);
  if (instance) {
    instance.dispose();
    instance = null;
  }
});

watch(
  () => props.option,
  () => {
    renderChart();
  },
  { deep: true }
);
</script>

<template>
  <div class="chart-root" ref="chartRef"></div>
</template>

<style scoped>
.chart-root {
  width: 100%;
  height: 260px;
}
</style>
